"""OCR port: the interface every OCR engine must satisfy.

Using :class:`typing.Protocol` keeps this a structural contract -- adapters do
not need to inherit from it, they just need a matching ``image_to_page``
method. This is pure standard library so the whole port layer imports offline.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..model import OcrPage

__all__ = ["OcrEngine"]


@runtime_checkable
class OcrEngine(Protocol):
    """Turn a single page image into an :class:`OcrPage` of word tokens.

    Implementations receive an opaque ``image`` object (whatever the paired
    rasterizer produces -- e.g. a PIL image, raw bytes, or in tests a simple
    placeholder) and the zero-based ``page_index`` of that image within the
    source document. They must return an :class:`OcrPage` whose tokens carry
    pixel coordinates and confidences so the extractor can reason about layout.
    """

    def image_to_page(self, image: Any, page_index: int) -> OcrPage:
        """Recognise ``image`` and return its tokens as an :class:`OcrPage`."""
        ...
