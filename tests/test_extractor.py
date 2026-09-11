"""Tests for the rule-based HEAVYCON PART I extractor.

These drive the real extraction code paths against synthetic Tesseract TSV
fixtures (no live Tesseract). They fail if the extractor logic is reverted.
"""

from __future__ import annotations

from pathlib import Path

from heavycon_analyzer.boxes import iter_boxes
from heavycon_analyzer.extractor import (
    collapse_spaces,
    extract_fields,
    fix_line_break_hyphenation,
    normalize_whitespace,
)
from heavycon_analyzer.model import ExtractedField, parse_tesseract_tsv

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_page(name: str, *, page_width: int, page_height: int = 3508):
    tsv = (_FIXTURES / name).read_text(encoding="utf-8")
    return parse_tesseract_tsv(
        tsv,
        page_index=0,
        page_width=page_width,
        page_height=page_height,
    )


def _by_box(fields: list[ExtractedField]) -> dict[int, ExtractedField]:
    return {f.box_no: f for f in fields}


# ---------------------------------------------------------------------------
# Main two-column fixture: every user-named field.
# ---------------------------------------------------------------------------

EXPECTED_VALUES = {
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


def test_all_user_named_fields_extracted() -> None:
    page = _load_page("heavycon_part1_page1.tsv", page_width=2480)
    fields = extract_fields([page], iter_boxes())
    by_box = _by_box(fields)

    for box_no, expected in EXPECTED_VALUES.items():
        assert (
            by_box[box_no].value == expected
        ), f"Box {box_no}: got {by_box[box_no].value!r}, expected {expected!r}"


def test_confidence_is_mean_of_value_tokens() -> None:
    page = _load_page("heavycon_part1_page1.tsv", page_width=2480)
    fields = extract_fields([page], iter_boxes())
    by_box = _by_box(fields)

    # Box 4 value tokens have conf 95.5, 95.0, 94.5 -> mean 95.0.
    assert by_box[4].confidence == 95.0
    # Every extracted (non-empty) field should carry a positive confidence.
    for box_no in EXPECTED_VALUES:
        assert by_box[box_no].confidence > 0


def test_box30_preserves_multiline_raw_text() -> None:
    page = _load_page("heavycon_part1_page1.tsv", page_width=2480)
    fields = extract_fields([page], iter_boxes())
    box30 = _by_box(fields)[30]

    expected = "Clauses 31 to 45 apply.\nRider clauses attached\nform part of this Charter."
    assert box30.value == expected
    assert box30.raw_text == expected
    # It must be genuinely multi-line.
    assert box30.value.count("\n") == 2
    assert box30.confidence > 0


def test_labels_and_full_coverage() -> None:
    page = _load_page("heavycon_part1_page1.tsv", page_width=2480)
    fields = extract_fields([page], iter_boxes())
    # One field per box definition, in the same order.
    assert [f.box_no for f in fields] == [b.box_no for b in iter_boxes()]
    by_box = _by_box(fields)
    assert by_box[2].korean_label == "용선주(Out)/선주"
    assert by_box[16].english_label == "Freight"


def test_deliberately_missing_box_yields_empty_value() -> None:
    page = _load_page("heavycon_part1_page1.tsv", page_width=2480)
    fields = extract_fields([page], iter_boxes())
    by_box = _by_box(fields)
    # Box 24 (Insurance) is not present anywhere in the fixture.
    assert by_box[24].value == ""
    assert by_box[24].raw_text == ""
    assert by_box[24].confidence == 0.0


def test_extractor_never_raises_on_empty_input() -> None:
    fields = extract_fields([], iter_boxes())
    assert len(fields) == len(iter_boxes())
    assert all(f.value == "" and f.confidence == 0.0 for f in fields)


# ---------------------------------------------------------------------------
# OCR-confusion fixture.
# ---------------------------------------------------------------------------


def test_ocr_confusion_header_matches_box() -> None:
    # Header 'l6. Freight' (letter L instead of 1) must still match Box 16,
    # 'I8. Free time' must match Box 18, and '3O.' (letter O) Box 30.
    page = _load_page("heavycon_part1_ocrnoise.tsv", page_width=1600)
    fields = extract_fields([page], iter_boxes())
    by_box = _by_box(fields)

    assert by_box[16].value == "EUR 1,750,000"
    assert by_box[16].confidence > 0
    assert by_box[18].value == "48 hours"
    box30 = by_box[30]
    assert box30.value == "See riders 11 to 20\nSpecial warranties included"
    assert box30.value.count("\n") == 1


def test_ocr_confusion_fixture_missing_boxes_empty() -> None:
    page = _load_page("heavycon_part1_ocrnoise.tsv", page_width=1600)
    fields = extract_fields([page], iter_boxes())
    by_box = _by_box(fields)
    # Cargo (Box 5) is absent from this fixture.
    assert by_box[5].value == ""
    assert by_box[5].confidence == 0.0


# ---------------------------------------------------------------------------
# Regression: merged number+label token (issue 1).
#
# Real Tesseract often emits the box number glued onto the first label word in
# tight form cells: "16.Freight" as a single token. The old header matcher
# required the number to be a standalone token, so the box silently dropped to
# an empty value. These tests fail on the pre-fix extractor and pass after the
# glued-token splitter was added.
# ---------------------------------------------------------------------------


def test_merged_number_label_token_extracts_value() -> None:
    page = _load_page("heavycon_part1_merged.tsv", page_width=1600)
    by_box = _by_box(extract_fields([page], iter_boxes()))

    # "16.Freight" glued header, value on the line below.
    assert by_box[16].value == "USD 2,500,000 lumpsum"
    assert by_box[16].confidence > 0


def test_merged_number_label_token_with_ocr_confusion() -> None:
    # "l8.Free time" -> Box 18 (letter L glued to 8), "3O.Additional ..." ->
    # Box 30 (letter O glued to 3). The glued splitter must still run the
    # OCR-confusion digit repair on the peeled prefix.
    page = _load_page("heavycon_part1_merged.tsv", page_width=1600)
    by_box = _by_box(extract_fields([page], iter_boxes()))

    assert by_box[18].value == "72 hours"
    assert by_box[18].confidence > 0
    # Box 30 is raw_text_only: the glued header word must not leak into the
    # value, and the multi-line block is captured verbatim.
    assert by_box[30].value == "See riders 31 to 45"
    assert by_box[30].confidence > 0


# ---------------------------------------------------------------------------
# Regression: same-line inline-value fallback (issue 2).
#
# When the value sits on the SAME line as the header ("16. Freight USD 5,000"),
# the old greedy label detection counted the value words as label and returned
# an empty value. The fallback now anchors the label at the start and stops at
# the first value-looking token. These tests fail on the pre-fix extractor.
# ---------------------------------------------------------------------------


def test_inline_value_on_header_line_separate_number() -> None:
    page = _load_page("heavycon_part1_inline.tsv", page_width=1600)
    by_box = _by_box(extract_fields([page], iter_boxes()))

    # "16. Freight USD 5,000" all on one line -> value "USD 5,000".
    assert by_box[16].value == "USD 5,000"
    assert by_box[16].confidence > 0
    # "18. Free time 48 hours" all on one line -> "48 hours".
    assert by_box[18].value == "48 hours"
    assert by_box[18].confidence > 0


def test_inline_value_on_header_line_glued_number() -> None:
    # "19.Demurrage rate USD 35,000": number glued to the label AND the value
    # inline on the same line -> "USD 35,000".
    page = _load_page("heavycon_part1_inline.tsv", page_width=1600)
    by_box = _by_box(extract_fields([page], iter_boxes()))

    assert by_box[19].value == "USD 35,000"
    assert by_box[19].confidence > 0


# ---------------------------------------------------------------------------
# Normalisation helper unit tests.
# ---------------------------------------------------------------------------


def test_collapse_spaces() -> None:
    assert collapse_spaces("  a   b\tc \n d ") == "a b c d"


def test_fix_line_break_hyphenation() -> None:
    assert fix_line_break_hyphenation("demob-\nilisation") == "demobilisation"
    # A hyphen not at a line break is preserved.
    assert fix_line_break_hyphenation("float-on") == "float-on"


def test_normalize_whitespace_preserves_lines() -> None:
    text = "  line one  \n\n\n  line   two \n\n"
    assert normalize_whitespace(text) == "line one\nline two"
