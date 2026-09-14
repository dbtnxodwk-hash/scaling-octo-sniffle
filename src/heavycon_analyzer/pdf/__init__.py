"""PDF rasterizer ports and adapters.

The :mod:`port` module defines the
:class:`~heavycon_analyzer.pdf.port.PdfRasterizer` Protocol; the
:mod:`rasterizer_adapter` module provides a real adapter that lazily imports
PyMuPDF (preferred) or pdf2image+poppler. No third-party package is imported at
module import time, so ``import heavycon_analyzer.pdf`` always succeeds offline.
"""

from __future__ import annotations

from .port import DEFAULT_DPI, PdfRasterizer
from .rasterizer_adapter import PdfiumOrPopplerRasterizer

__all__ = ["PdfRasterizer", "DEFAULT_DPI", "PdfiumOrPopplerRasterizer"]
