"""End-to-end pipeline tests using the fixture OCR engine + a fake rasterizer.

The real Tesseract/PDF path cannot run in the offline sandbox (no Tesseract,
no PyMuPDF/poppler, no network). These tests instead:

1. Drive :func:`analyze_pdf` with a fake rasterizer (placeholder page objects)
   and :class:`FixtureOcrEngine` built from the FEAT-002 TSV fixtures, and
   assert the full pipeline yields the expected ExtractedField values.
2. Assert that the real adapters (TesseractOcrEngine, PdfiumOrPopplerRasterizer)
   raise the documented RuntimeError when their dependency/engine is absent --
   which is exactly the case in this sandbox.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from heavycon_analyzer.boxes import iter_boxes
from heavycon_analyzer.model import ExtractedField, parse_tesseract_tsv
from heavycon_analyzer.ocr.fixture_adapter import FixtureOcrEngine
from heavycon_analyzer.ocr.tesseract_adapter import (
    MISSING_TESSERACT_MESSAGE,
    TesseractOcrEngine,
)
from heavycon_analyzer.pdf.rasterizer_adapter import (
    MISSING_RASTERIZER_MESSAGE,
    PdfiumOrPopplerRasterizer,
)
from heavycon_analyzer.pipeline import analyze_pdf, build_default_pipeline

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


class _FakeRasterizer:
    """Fake PDF rasterizer returning opaque placeholder page objects.

    It records the DPI it was called with so we can assert the pipeline passes
    the configured value through. The placeholder objects stand in for the
    images a real rasterizer would produce; the FixtureOcrEngine ignores them.
    """

    def __init__(self, page_count: int) -> None:
        self.page_count = page_count
        self.render_calls: list[tuple[str, int]] = []

    def render(self, pdf_path: str, dpi: int = 300) -> list[object]:
        self.render_calls.append((pdf_path, dpi))
        return [object() for _ in range(self.page_count)]


def _by_box(fields: list[ExtractedField]) -> dict[int, ExtractedField]:
    return {f.box_no: f for f in fields}


# Expected values mirror the FEAT-002 extractor fixture (single source page).
_EXPECTED_VALUES = {
    2: "Heavylift Carriers AS Oslo, Norway",
    3: "Oceanic Projects Ltd Houston, USA",
    4: "MV Blue Marlin",
    5: "Offshore jacket structure",
    6: "Ulsan, South Korea",
    7: "Rotterdam, Netherlands",
    8: "Float-on float-off",
    9: "Skidding ashore",
    10: "60 days",
    11: "14 days notice",
    12: "7 days prior",
    13: "5 days prior",
    15: "GL Noble Denton",
    16: "USD 2,500,000 lumpsum",
    17: "100% within 5 banking days",
    18: "72 hours",
    19: "USD 35,000 per day",
    20: "USD 400,000",
    21: "USD 350,000",
    22: "Charterers account",
    23: "Applicable above USD 600",
}


# ---------------------------------------------------------------------------
# End-to-end pipeline via fixture adapter + fake rasterizer.
# ---------------------------------------------------------------------------


def test_analyze_pdf_end_to_end_with_fixture() -> None:
    page = parse_tesseract_tsv(
        (_FIXTURES / "heavycon_part1_page1.tsv").read_text(encoding="utf-8"),
        page_index=0,
        page_width=2480,
        page_height=3508,
    )
    rasterizer = _FakeRasterizer(page_count=1)
    ocr_engine = FixtureOcrEngine([page])

    fields = analyze_pdf(
        "dummy.pdf",
        rasterizer=rasterizer,
        ocr_engine=ocr_engine,
        boxes=iter_boxes(),
    )
    by_box = _by_box(fields)

    for box_no, expected in _EXPECTED_VALUES.items():
        assert (
            by_box[box_no].value == expected
        ), f"Box {box_no}: got {by_box[box_no].value!r}, expected {expected!r}"

    # Box 30 special provisions preserved as multi-line raw text.
    assert by_box[30].value == (
        "Clauses 31 to 45 apply.\nRider clauses attached\nform part of this Charter."
    )


def test_analyze_pdf_returns_full_box_list() -> None:
    page = parse_tesseract_tsv(
        (_FIXTURES / "heavycon_part1_page1.tsv").read_text(encoding="utf-8"),
        page_index=0,
        page_width=2480,
        page_height=3508,
    )
    fields = analyze_pdf(
        "dummy.pdf",
        rasterizer=_FakeRasterizer(page_count=1),
        ocr_engine=FixtureOcrEngine([page]),
    )
    # One field per box definition, in box order (defaults to full Box 1-30).
    assert [f.box_no for f in fields] == [b.box_no for b in iter_boxes()]
    assert len(fields) == len(iter_boxes())


def test_analyze_pdf_passes_dpi_to_rasterizer() -> None:
    page = parse_tesseract_tsv(
        (_FIXTURES / "heavycon_part1_page1.tsv").read_text(encoding="utf-8"),
        page_index=0,
        page_width=2480,
    )
    rasterizer = _FakeRasterizer(page_count=1)
    analyze_pdf(
        "charter.pdf",
        rasterizer=rasterizer,
        ocr_engine=FixtureOcrEngine([page]),
        dpi=400,
    )
    assert rasterizer.render_calls == [("charter.pdf", 400)]


def test_analyze_pdf_default_dpi_is_300() -> None:
    page = parse_tesseract_tsv(
        (_FIXTURES / "heavycon_part1_page1.tsv").read_text(encoding="utf-8"),
        page_index=0,
        page_width=2480,
    )
    rasterizer = _FakeRasterizer(page_count=1)
    analyze_pdf(
        "charter.pdf",
        rasterizer=rasterizer,
        ocr_engine=FixtureOcrEngine([page]),
    )
    assert rasterizer.render_calls == [("charter.pdf", 300)]


def test_fixture_engine_from_tsv_files() -> None:
    engine = FixtureOcrEngine.from_tsv_files(
        [_FIXTURES / "heavycon_part1_page1.tsv"],
        page_sizes=[(2480, 3508)],
    )
    assert len(engine) == 1
    fields = analyze_pdf(
        "dummy.pdf",
        rasterizer=_FakeRasterizer(page_count=1),
        ocr_engine=engine,
    )
    assert _by_box(fields)[4].value == "MV Blue Marlin"


def test_fixture_engine_out_of_range_returns_empty_page() -> None:
    page = parse_tesseract_tsv(
        (_FIXTURES / "heavycon_part1_page1.tsv").read_text(encoding="utf-8"),
        page_index=0,
        page_width=2480,
    )
    engine = FixtureOcrEngine([page])
    empty = engine.image_to_page(object(), page_index=5)
    assert empty.tokens == []
    assert empty.page_index == 5


# ---------------------------------------------------------------------------
# Real adapters must fail clearly when their dependency/engine is absent.
# ---------------------------------------------------------------------------


def test_tesseract_engine_raises_clear_error_without_dependency() -> None:
    engine = TesseractOcrEngine(language="eng")
    with pytest.raises(RuntimeError) as excinfo:
        engine.image_to_page(object(), page_index=0)
    assert str(excinfo.value) == MISSING_TESSERACT_MESSAGE
    assert "README" in str(excinfo.value)


def test_rasterizer_raises_clear_error_without_backend() -> None:
    rasterizer = PdfiumOrPopplerRasterizer()
    with pytest.raises(RuntimeError) as excinfo:
        rasterizer.render("charter.pdf")
    assert str(excinfo.value) == MISSING_RASTERIZER_MESSAGE
    assert "README" in str(excinfo.value)


def test_build_default_pipeline_constructs_real_adapters() -> None:
    # The factory must succeed offline (adapters defer their third-party
    # imports until first use).
    pipeline = build_default_pipeline(language="eng", tesseract_cmd=None)
    assert isinstance(pipeline["ocr_engine"], TesseractOcrEngine)
    assert isinstance(pipeline["rasterizer"], PdfiumOrPopplerRasterizer)
    assert pipeline["ocr_engine"].language == "eng"

    # And running it in this sandbox surfaces the documented rasterizer error
    # first (rasterization happens before OCR).
    with pytest.raises(RuntimeError) as excinfo:
        analyze_pdf("charter.pdf", **pipeline)
    assert str(excinfo.value) == MISSING_RASTERIZER_MESSAGE
