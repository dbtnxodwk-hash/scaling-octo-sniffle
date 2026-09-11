"""End-to-end pipeline: scanned PDF -> OCR -> extracted HEAVYCON fields.

This module wires the ports together and stays import-safe offline: it imports
only the ports and pure extractor at module load, and constructs the real
third-party-backed adapters lazily inside :func:`build_default_pipeline`.

Typical use on a real machine::

    fields = analyze_pdf("charter.pdf", **build_default_pipeline())

In tests/demos the same :func:`analyze_pdf` runs against the
:class:`~heavycon_analyzer.ocr.fixture_adapter.FixtureOcrEngine` and a fake
rasterizer, so the whole orchestration is verifiable with zero dependencies.
"""

from __future__ import annotations

from typing import Any

from .boxes import BoxDefinition, iter_boxes
from .extractor import extract_fields
from .model import ExtractedField, OcrPage
from .ocr.port import OcrEngine
from .pdf.port import DEFAULT_DPI, PdfRasterizer

__all__ = ["analyze_pdf", "build_default_pipeline"]


def analyze_pdf(
    pdf_path: str,
    *,
    rasterizer: PdfRasterizer,
    ocr_engine: OcrEngine,
    boxes: list[BoxDefinition] | None = None,
    dpi: int = DEFAULT_DPI,
) -> list[ExtractedField]:
    """Analyse a scanned PDF and return the HEAVYCON PART I box fields.

    Orchestration: rasterize the PDF to page images, OCR each image into an
    :class:`~heavycon_analyzer.model.OcrPage`, then run the pure
    :func:`~heavycon_analyzer.extractor.extract_fields` over all pages.

    Args:
        pdf_path: Path to the scanned PDF.
        rasterizer: A :class:`~heavycon_analyzer.pdf.port.PdfRasterizer`.
        ocr_engine: An :class:`~heavycon_analyzer.ocr.port.OcrEngine`.
        boxes: Box definitions to extract; defaults to the full HEAVYCON 2007
            PART I Box 1-30 layout.
        dpi: Rasterization DPI (default :data:`DEFAULT_DPI`, 300).

    Returns:
        One :class:`~heavycon_analyzer.model.ExtractedField` per box definition,
        in box order. Missing boxes yield empty values (the extractor never
        raises on absent boxes).
    """
    if boxes is None:
        boxes = iter_boxes()

    images: list[Any] = rasterizer.render(pdf_path, dpi=dpi)

    pages: list[OcrPage] = [
        ocr_engine.image_to_page(image, page_index) for page_index, image in enumerate(images)
    ]

    return extract_fields(pages, boxes)


def build_default_pipeline(
    *,
    language: str = "eng",
    tesseract_cmd: str | None = None,
    poppler_path: str | None = None,
) -> dict[str, Any]:
    """Construct the real adapters for use with :func:`analyze_pdf`.

    The third-party-backed adapters are imported here (still lazily relative to
    module load) and returned as keyword arguments so a caller can splat them::

        fields = analyze_pdf(path, **build_default_pipeline())

    The adapters themselves defer their third-party imports until first use, so
    calling this factory does not require Tesseract/PyMuPDF to be installed --
    only actually running the pipeline does.

    Args:
        language: Tesseract language code(s) (default ``"eng"``).
        tesseract_cmd: Optional path to the ``tesseract`` executable (Windows).
        poppler_path: Optional poppler ``bin`` path for the pdf2image fallback.

    Returns:
        A dict with ``rasterizer`` and ``ocr_engine`` ready to pass to
        :func:`analyze_pdf`.
    """
    from .ocr.tesseract_adapter import TesseractOcrEngine
    from .pdf.rasterizer_adapter import PdfiumOrPopplerRasterizer

    return {
        "rasterizer": PdfiumOrPopplerRasterizer(poppler_path=poppler_path),
        "ocr_engine": TesseractOcrEngine(
            language=language,
            tesseract_cmd=tesseract_cmd,
        ),
    }
