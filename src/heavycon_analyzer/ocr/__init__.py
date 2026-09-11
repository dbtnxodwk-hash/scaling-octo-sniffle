"""OCR ports and adapters.

The :mod:`port` module defines the :class:`~heavycon_analyzer.ocr.port.OcrEngine`
Protocol. Concrete adapters live alongside it:

* :mod:`tesseract_adapter` -- real Tesseract engine (lazy third-party imports).
* :mod:`fixture_adapter` -- pre-parsed pages for tests and demos (stdlib only).

Nothing here imports a third-party package at module import time, so
``import heavycon_analyzer.ocr`` always succeeds offline.
"""

from __future__ import annotations

from .fixture_adapter import FixtureOcrEngine
from .port import OcrEngine

__all__ = ["OcrEngine", "FixtureOcrEngine"]
