from __future__ import annotations

from pathlib import Path
from typing import Any

from ..llm.base import tool_result_message
from ..tools import coherence, golden, ingestion, isin as isin_tool
from ..tools.registry import TOOLS
from ..tools.submit import submit_record
from .prompts import EXTRACTOR_SYSTEM, build_user_message

TEXT_PREVIEW_CHARS = 8000
REQUIRED_BEFORE_SUBMIT = {"validate_isin", "lookup_golden_record", "check_date_coherence"}
VALIDATION_REMINDER = "Use as tools de validação e finalize com submit_record."


def _missing_args(args: dict[str, Any], *required: str) -> list[str]:
    return [key for key in required if args.get(key) in (None, "")]


def _tool_names() -> list[str]:
    return [tool["function"]["name"] for tool in TOOLS]


class ToolExecutor:
    def __init__(self, golden_path: str, ocr_lang: str, tracer, allowed_root: Path | None = None):
        self.golden_path = golden_path
        self.ocr_lang = ocr_lang
        self.tracer = tracer
        self.allowed_root = allowed_root
        self.called: set[str] = set()
        self.ingestion_meta = {"method": "text_native", "ocr_engine": None,
                               "pages": None, "ocr_confidence": None}
        self.document_text = ""

    def _path_allowed(self, pdf_path: str) -> bool:
        if self.allowed_root is None:
            return True
        try:
            return Path(pdf_path).resolve().is_relative_to(self.allowed_root)
        except (OSError, ValueError):
            return False

    def run(self, step: int, name: str, args: dict[str, Any] | None) -> dict:
        safe_args = args or {}
        self.tracer.tool_call(step, name, safe_args)
        result = self._dispatch(step, name, safe_args)
        self.called.add(name)
        self.tracer.tool_result(step, name, result)
        return result

    def _dispatch(self, step: int, name: str, args: dict[str, Any]) -> dict:
        if name == "read_document":
            missing = _missing_args(args, "pdf_path")
            if missing:
                return {"error": f"argumentos obrigatórios ausentes: {missing}"}
            if not self._path_allowed(args["pdf_path"]):
                return {"error": "caminho fora do diretório permitido"}
            result = ingestion.read_document(args["pdf_path"])
            self.ingestion_meta["pages"] = result.get("num_pages")
            if result.get("text", "").strip():
                self.document_text = result["text"]
            return {
                "has_text_layer": result["has_text_layer"],
                "num_pages": result["num_pages"],
                "method": result["method"],
                "text": result["text"][:TEXT_PREVIEW_CHARS],
            }

        if name == "read_page":
            missing = _missing_args(args, "pdf_path", "page_number")
            if missing:
                return {"error": f"argumentos obrigatórios ausentes: {missing}"}
            if not self._path_allowed(args["pdf_path"]):
                return {"error": "caminho fora do diretório permitido"}
            try:
                page_number = int(args["page_number"])
            except (TypeError, ValueError):
                return {"error": f"page_number inválido: {args['page_number']!r}"}
            return ingestion.read_page(args["pdf_path"], page_number)

        if name == "run_ocr":
            missing = _missing_args(args, "pdf_path")
            if missing:
                return {"error": f"argumentos obrigatórios ausentes: {missing}"}
            if not self._path_allowed(args["pdf_path"]):
                return {"error": "caminho fora do diretório permitido"}
            result = ingestion.run_ocr(args["pdf_path"], lang=self.ocr_lang)
            self.ingestion_meta["method"] = "ocr"
            self.ingestion_meta["ocr_engine"] = (
                result.get("ocr_engine") if result.get("available") else "indisponível"
            )
            self.ingestion_meta["ocr_confidence"] = result.get("ocr_confidence")
            if result.get("available"):
                self.ingestion_meta["pages"] = result.get("num_pages")
                if result.get("text", "").strip():
                    self.document_text = result["text"]
            return {
                key: value
                for key, value in result.items()
                if key != "text"
            } | {"text": (result.get("text") or "")[:TEXT_PREVIEW_CHARS]}

        if name == "validate_isin":
            return isin_tool.validate_isin(args.get("isin", ""))

        if name == "lookup_golden_record":
            return golden.lookup_golden_record(
                self.golden_path,
                isin=args.get("isin", ""),
                ticker=args.get("ticker", ""),
                cnpj=args.get("cnpj", ""),
                issuer=args.get("issuer", ""),
            )

        if name == "check_date_coherence":
            return coherence.check_date_coherence(args.get("dates", {}))

        if name == "check_value_coherence":
            return coherence.check_value_coherence(
                args.get("kind", "none"),
                args.get("gross_value"),
                args.get("net_value"),
                args.get("irrf_rate"),
            )

        if name == "log_reasoning":
            self.tracer.reasoning(step, args.get("thought", ""), args.get("phase"))
            return {"ok": True}

        if name == "submit_record":
            return submit_record(args)

        return {"error": f"tool desconhecida: {name}"}


def _blocked_submit_result(missing: set[str]) -> dict:
    return {"ok": False, "error": f"rode as validações antes de submeter: {sorted(missing)}"}


def run_agent(document_id, source_file, llm, config, tracer, lens: str | None = None) -> dict:
    allowed_root = Path(source_file).resolve().parent
    executor = ToolExecutor(config["golden_path"], config.get("ocr", {}).get("lang", "por"),
                            tracer, allowed_root)
    messages = [
        {"role": "system", "content": EXTRACTOR_SYSTEM},
        {"role": "user", "content": build_user_message(document_id, source_file, lens)},
    ]
    max_steps = config.get("max_steps", 12)
    tokens, tool_calls_log = 0, []
    submission = None

    for step in range(max_steps):
        tracer.llm_request(step, len(messages), _tool_names())
        response = llm.chat(messages, TOOLS)
        tokens += (response.usage or {}).get("total_tokens", 0) or 0
        tracer.llm_response(
            step,
            response.content,
            [tool_call.name for tool_call in response.tool_calls],
            response.usage,
        )
        messages.append(response.assistant_message)

        if not response.tool_calls:
            messages.append({"role": "user", "content": VALIDATION_REMINDER})
            continue

        for tool_call in response.tool_calls:
            tool_calls_log.append({"step": step, "name": tool_call.name})

            if tool_call.name == "submit_record":
                missing = REQUIRED_BEFORE_SUBMIT - executor.called
                if missing:
                    result = _blocked_submit_result(missing)
                    executor.tracer.tool_call(step, tool_call.name, tool_call.arguments)
                    executor.tracer.tool_result(step, tool_call.name, result)
                    messages.append(tool_result_message(tool_call.id, result))
                    continue

            result = executor.run(step, tool_call.name, tool_call.arguments)
            messages.append(tool_result_message(tool_call.id, result))

            if tool_call.name == "submit_record" and result.get("ok"):
                submission = result["submission"]
                return {
                    "submission": submission,
                    "steps": step + 1,
                    "tool_calls": tool_calls_log,
                    "tokens": tokens,
                    "ingestion": executor.ingestion_meta,
                    "document_text": executor.document_text,
                    "terminated": True,
                    "validations_called": sorted(executor.called),
                }

    tracer.log("budget_exceeded", max_steps=max_steps)
    return {
        "submission": submission,
        "steps": max_steps,
        "tool_calls": tool_calls_log,
        "tokens": tokens,
        "ingestion": executor.ingestion_meta,
        "document_text": executor.document_text,
        "terminated": False,
        "validations_called": sorted(executor.called),
    }
