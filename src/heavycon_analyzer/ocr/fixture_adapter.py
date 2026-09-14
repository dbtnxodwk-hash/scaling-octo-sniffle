"""Fixture OCR adapter: serve pre-parsed pages without a real engine.

This lets the full pipeline be exercised end-to-end in tests and demos with no
Tesseract binary and no third-party packages. It is pure standard library.

A :class:`FixtureOcrEngine` holds one :class:`OcrPage` per document page and
returns them in order as the pipeline OCRs each rasterised image. The
placeholder ``image`` objects handed in by a fake rasterizer are ignored except
for bookkeeping -- the tokens come entirely from the pre-parsed pages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..model import OcrPage, parse_tesseract_tsv

__all__ = ["FixtureOcrEngine"]


class FixtureOcrEngine:
    """Return canned :class:`OcrPage` objects, one per call, in order.

    The engine satisfies the :class:`~heavycon_analyzer.ocr.port.OcrEngine`
    Protocol structurally, so it is a drop-in stand-in for the real Tesseract
    engine in tests and demos.
    """

    def __init__(self, pages: list[OcrPage]) -> None:
        self._pages = list(pages)

    @classmethod
    def from_tsv_files(
        cls,
        paths: list[str | Path],
        *,
        page_sizes: list[tuple[int, int]] | None = None,
        encoding: str = "utf-8",
    ) -> FixtureOcrEngine:
        """Build an engine from Tesseract TSV fixture files.

        Args:
            paths: TSV fixture file paths, one per page, in document order.
            page_sizes: Optional ``(width, height)`` per page, matching
                ``paths`` by position. When omitted the page geometry is left
                at ``0`` (the extractor then treats the page as single-column).
            encoding: Text encoding of the fixture files.
        """
        pages: list[OcrPage] = []
        for idx, path in enumerate(paths):
            tsv_text = Path(path).read_text(encoding=encoding)
            if page_sizes is not None and idx < len(page_sizes):
                width, height = page_sizes[idx]
            else:
                width, height = 0, 0
            pages.append(
                parse_tesseract_tsv(
                    tsv_text,
                    page_index=idx,
                    page_width=width,
                    page_height=height,
                )
            )
        return cls(pages)

    def image_to_page(self, image: Any, page_index: int) -> OcrPage:
        """Return the pre-parsed page for ``page_index``.

        The ``image`` argument is accepted for Protocol compatibility but is
        not used; the tokens come from the canned pages. If a caller requests a
        page index beyond what was supplied, an empty page is returned so the
        pipeline stays robust.
        """
        for page in self._pages:
            if page.page_index == page_index:
                return page
        if 0 <= page_index < len(self._pages):
            return self._pages[page_index]
        return OcrPage(page_index=page_index, width=0, height=0, tokens=[])

    def __len__(self) -> int:
        return len(self._pages)
