from __future__ import annotations

import threading
from contextlib import suppress
from functools import lru_cache

import numpy as np  # type: ignore
import pdfplumber  # type: ignore
import pypdfium2 as pdfium  # type: ignore
from rapidocr_onnxruntime import RapidOCR  # type: ignore

OCR_RENDER_SCALE = 3.0

_OCR_ENGINE = None
_OCR_LOCK = threading.Lock()


@lru_cache(maxsize=32)
def read_document(pdf_path: str) -> dict:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    full_text = "\n".join(pages)
    return {
        "text": full_text,
        "num_pages": len(pages),
        "has_text_layer": len(full_text.strip()) > 0,
        "method": "text_native",
    }


def read_page(pdf_path: str, page_number: int) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        if page_number < 1 or page_number > len(pdf.pages):
            return {"error": f"página {page_number} fora do intervalo (1..{len(pdf.pages)})"}
        text = pdf.pages[page_number - 1].extract_text() or ""
    return {"page": page_number, "text": text, "method": "text_native"}


def _get_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        with _OCR_LOCK:
            if _OCR_ENGINE is None:
                _OCR_ENGINE = RapidOCR()
    return _OCR_ENGINE


def _render_page(page, render_scale: float):
    bitmap = page.render(scale=render_scale)
    return np.array(bitmap.to_pil().convert("RGB"))


@lru_cache(maxsize=32)
def run_ocr(pdf_path: str, lang: str = "por", render_scale: float = OCR_RENDER_SCALE) -> dict:
    try:
        engine = _get_engine()
    except Exception as exc:
        return {
            "text": "",
            "method": "ocr",
            "available": False,
            "ocr_engine": "rapidocr",
            "error": f"OCR indisponível: {exc}",
        }

    pdf = None
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        pages = []
        scores: list[float] = []
        for page in pdf:
            result, _ = engine(_render_page(page, render_scale))
            if result:
                pages.append("\n".join(line[1] for line in result))
                scores.extend(float(line[2]) for line in result if len(line) > 2)
            else:
                pages.append("")
    except Exception as exc:
        return {
            "text": "",
            "method": "ocr",
            "available": False,
            "ocr_engine": "rapidocr",
            "error": f"falha no OCR: {exc}",
        }
    finally:
        if pdf is not None:
            with suppress(Exception):
                pdf.close()

    full_text = "\n".join(pages)
    return {
        "text": full_text,
        "num_pages": len(pages),
        "has_text_layer": len(full_text.strip()) > 0,
        "method": "ocr",
        "ocr_engine": "rapidocr(pp-ocr/onnx)",
        "available": True,
        "lang": lang,
        "ocr_confidence": round(sum(scores) / len(scores), 3) if scores else None,
    }
