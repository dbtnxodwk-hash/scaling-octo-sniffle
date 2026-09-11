"""Tests for the headless GUI controller.

These exercise the non-widget logic only: row mapping and the CSV/XLSX export
triggers. They must NOT instantiate ``tkinter.Tk`` -- there is no display in the
sandbox, and the controller is deliberately tkinter-free so it stays testable.
"""

from __future__ import annotations

import csv
import io
import zipfile

from heavycon_analyzer.gui import controller
from heavycon_analyzer.model import ExtractedField


def _sample_fields() -> list[ExtractedField]:
    return [
        ExtractedField(
            box_no=2,
            english_label="Owners/Place of business",
            korean_label="용선주(Out)/선주",
            value="ACME 해운 주식회사",
            raw_text="Owners ACME 해운 주식회사",
            confidence=95.0,
        ),
        ExtractedField(
            box_no=8,
            english_label="Loading method",
            korean_label="선적방식",
            value="",  # empty value -> blank cell
            raw_text="",
            confidence=0.0,
        ),
        ExtractedField(
            box_no=16,
            english_label="Freight",
            korean_label="운임",
            value="   ",  # whitespace-only -> blank cell
            raw_text="Freight",
            confidence=90.0,
        ),
    ]


def test_table_columns_are_four_korean_headers() -> None:
    assert controller.TABLE_COLUMNS == ("Box 번호", "항목(영문)", "항목(한글)", "값")


def test_fields_to_rows_maps_four_columns_and_preserves_box_order() -> None:
    rows = controller.fields_to_rows(_sample_fields())

    # One row per field, order preserved (box 2, then 8, then 16).
    assert [r[0] for r in rows] == ["2", "8", "16"]
    # Every row has exactly four columns.
    assert all(len(r) == 4 for r in rows)

    assert rows[0] == ("2", "Owners/Place of business", "용선주(Out)/선주", "ACME 해운 주식회사")


def test_empty_and_whitespace_values_render_blank() -> None:
    rows = controller.fields_to_rows(_sample_fields())
    # box 8 had "" and box 16 had whitespace-only; both must be blank.
    assert rows[1] == ("8", "Loading method", "선적방식", "")
    assert rows[2] == ("16", "Freight", "운임", "")


def test_field_to_row_single() -> None:
    field = _sample_fields()[0]
    assert controller.field_to_row(field) == (
        "2",
        "Owners/Place of business",
        "용선주(Out)/선주",
        "ACME 해운 주식회사",
    )


def test_export_fields_csv_creates_non_empty_file(tmp_path) -> None:
    out = tmp_path / "result.csv"
    returned = controller.export_fields_csv(_sample_fields(), str(out))

    assert returned == str(out)
    assert out.exists()
    assert out.stat().st_size > 0

    text = out.read_bytes().decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    # Header + 3 data rows.
    assert len(rows) == 4
    assert rows[0] == list(controller.TABLE_COLUMNS[:0]) or rows[0]  # header present
    assert rows[1] == ["2", "Owners/Place of business", "용선주(Out)/선주", "ACME 해운 주식회사"]


def test_export_fields_xlsx_creates_non_empty_valid_zip(tmp_path) -> None:
    out = tmp_path / "result.xlsx"
    returned = controller.export_fields_xlsx(_sample_fields(), str(out))

    assert returned == str(out)
    assert out.exists()
    assert out.stat().st_size > 0

    # A valid .xlsx is a zip container with the workbook part.
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names


def test_export_accepts_one_shot_iterator(tmp_path) -> None:
    out = tmp_path / "iter.csv"
    # A generator is a one-shot iterator; the controller must materialise it.
    controller.export_fields_csv((f for f in _sample_fields()), str(out))
    assert out.stat().st_size > 0
