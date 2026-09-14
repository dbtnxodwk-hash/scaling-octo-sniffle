"""Real PDF rasterizer adapter.

Rendering a scanned PDF to page images needs a third-party library plus (for
the pdf2image path) the poppler binaries. Those are only available on a real
machine, so the imports here are LAZY: they happen inside
:meth:`PdfiumOrPopplerRasterizer.render`, never at module import time. This
keeps the package importable in a fully offline sandbox.

Backend preference:

1. **PyMuPDF** (``fitz``) -- single wheel, no external binaries, fast. Tried
   first.
2. **pdf2image + poppler** -- fallback; needs the poppler ``pdftoppm`` binary
   installed on the system.

When neither backend is available a clear, actionable :class:`RuntimeError`
with install guidance is raised.
"""

from __future__ import annotations

from typing import Any

from .port import DEFAULT_DPI

__all__ = ["PdfiumOrPopplerRasterizer", "MISSING_RASTERIZER_MESSAGE"]

# Shown when no rasterizer backend can be loaded. Module constant so tests can
# assert on it and the wording stays consistent with the README.
MISSING_RASTERIZER_MESSAGE = (
    "No PDF rasterizer backend available; install the `ocr` optional "
    "dependencies (PyMuPDF, or pdf2image plus the poppler binaries). See README."
)


class PdfiumOrPopplerRasterizer:
    """Rasterize PDFs to per-page images using PyMuPDF, else pdf2image.

    The adapter satisfies the
    :class:`~heavycon_analyzer.pdf.port.PdfRasterizer` Protocol structurally.

    Args:
        poppler_path: Optional path to the poppler ``bin`` directory, used only
            for the pdf2image fallback (typical on Windows where poppler is not
            on ``PATH``). Ignored by the PyMuPDF backend.
    """

    def __init__(self, poppler_path: str | None = None) -> None:
        self.poppler_path = poppler_path

    def render(self, pdf_path: str, dpi: int = DEFAULT_DPI) -> list[Any]:
        """Render ``pdf_path`` to one image per page at ``dpi`` (default 300).

        Tries PyMuPDF first, then pdf2image+poppler.

        Raises:
            RuntimeError: if neither backend is available.
        """
        fitz_images = self._try_pymupdf(pdf_path, dpi)
        if fitz_images is not None:
            return fitz_images

        pdf2image_images = self._try_pdf2image(pdf_path, dpi)
        if pdf2image_images is not None:
            return pdf2image_images

        raise RuntimeError(MISSING_RASTERIZER_MESSAGE)

    def _try_pymupdf(self, pdf_path: str, dpi: int) -> list[Any] | None:
        """Render via PyMuPDF/fitz; return None if the backend is unavailable."""
        try:
            import fitz  # noqa: PLC0415  (intentional lazy import)
        except Exception:
            return None

        images: list[Any] = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                # ``dpi`` keyword on get_pixmap handles the zoom for us.
                pixmap = page.get_pixmap(dpi=dpi)
                images.append(pixmap)
        return images

    def _try_pdf2image(self, pdf_path: str, dpi: int) -> list[Any] | None:
        """Render via pdf2image+poppler; return None if unavailable."""
        try:
            from pdf2image import convert_from_path  # noqa: PLC0415  (lazy import)
        except Exception:
            return None

        try:
            return list(
                convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    poppler_path=self.poppler_path,
                )
            )
        except Exception as exc:
            # pdf2image imported but poppler binary missing / render failed.
            raise RuntimeError(MISSING_RASTERIZER_MESSAGE) from exc
