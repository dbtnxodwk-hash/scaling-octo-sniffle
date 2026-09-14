"""PDF rasterizer port: convert a scanned PDF into per-page images.

A structural :class:`typing.Protocol` so any rasterizer with a matching
``render`` method can be plugged into the pipeline. Pure standard library --
imports offline with no third-party packages.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = ["PdfRasterizer", "DEFAULT_DPI"]

# 300 DPI is the recommended resolution for OCR quality: high enough for
# Tesseract to resolve small print, without ballooning memory/time.
DEFAULT_DPI = 300


@runtime_checkable
class PdfRasterizer(Protocol):
    """Render a PDF file to one image object per page.

    The returned image objects are opaque -- their concrete type depends on the
    adapter (e.g. PIL images) and is only ever handed straight to the paired
    OCR engine's ``image_to_page``. Rendering DPI is configurable and defaults
    to :data:`DEFAULT_DPI` (300) for good OCR accuracy.
    """

    def render(self, pdf_path: str, dpi: int = DEFAULT_DPI) -> list[Any]:
        """Return one image object per page of ``pdf_path`` at ``dpi``."""
        ...
