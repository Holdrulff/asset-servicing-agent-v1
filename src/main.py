from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

import yaml
from dotenv import load_dotenv

from .agent.harness import process_document
from .llm.factory import make_client
from .output.report import build_report
from .output.writer import write_record


DEFAULT_CONFIG_PATH = "config.yaml"
DEFAULT_DOCUMENTS_DIR = "data/documents"
DEFAULT_OUTPUT_DIR = "output"


def _doc_id(path: Path) -> str:
    return path.stem


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agente de extração de eventos corporativos")
    parser.add_argument("--documents", default=DEFAULT_DOCUMENTS_DIR)
    parser.add_argument("--golden", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--trace", action="store_true",
                        help="grava o trace de auditoria em traces/<doc>.jsonl")
    return parser.parse_args(argv)


def _load_config(config_path: str, provider: str | None, golden_path: str | None) -> dict[str, Any]:
    load_dotenv()
    raw_config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if not isinstance(raw_config, dict):
        raise ValueError(f"configuração inválida em {config_path}")

    config = dict(raw_config)
    if provider:
        config["provider"] = provider
    if golden_path:
        config["golden_path"] = golden_path
    return config


def _find_documents(documents_dir: str) -> list[Path]:
    return sorted(Path(documents_dir).glob("*.pdf"))


def _process_documents(docs: list[Path], llm, config: dict[str, Any], output_dir: Path) -> dict[str, dict]:
    results: dict[str, dict] = {}
    max_workers = int(config.get("max_workers", 4))

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(process_document, _doc_id(path), str(path), llm, config, output_dir): path
            for path in docs
        }
        for future in as_completed(futures):
            document_id = _doc_id(futures[future])
            try:
                results[document_id] = future.result()
            except Exception as exc:
                print(f"  {document_id}  ERRO  {exc}")
    return results


def _write_outputs(docs: list[Path], results: dict[str, dict], output_dir: Path) -> dict:
    records_dir = output_dir / "records"
    records = []

    missing = [_doc_id(pdf) for pdf in docs if not results.get(_doc_id(pdf))]
    if missing:
        print(f"\n⚠️  {len(missing)} documento(s) sem record (falha não tratada): {missing}")

    for pdf in docs:
        document_id = _doc_id(pdf)
        result = results.get(document_id)
        if not result:
            continue

        write_record(result["record"], records_dir)
        records.append(result["record"])
        flag = "AUTO  " if result["outcome"] == "auto_approved" else "REVIEW"
        print(f"  {document_id}  {flag}  {', '.join(result['review_reasons']) or '-'}")

    return build_report(records, output_dir)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = _load_config(args.config, args.provider, args.golden)
    config["trace"] = args.trace
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    llm = make_client(config["provider"], config)
    docs = _find_documents(args.documents)
    if not docs:
        print(f"Nenhum PDF em {args.documents}")
        return 0

    max_workers = config.get("max_workers", 4)
    print(
        f"Provider: {config['provider']} | Modelo: "
        f"{config.get('providers', {}).get(config['provider'], {}).get('model')}"
    )
    print(f"Processando {len(docs)} documentos (max_workers={max_workers})...\n")

    results = _process_documents(docs, llm, config, output_dir)
    summary = _write_outputs(docs, results, output_dir)

    print(f"\nAuto-aprovados: {summary['auto_approved']}")
    print(f"Em revisão: {[r['document_id'] for r in summary['review']]}")
    artifacts = "records/  exceptions_report.md"
    if config.get("trace"):
        artifacts += "  traces/"
    print(f"\nArtefatos em {output_dir}/: {artifacts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
