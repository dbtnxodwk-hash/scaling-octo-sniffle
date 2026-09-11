"""Tests for the pure-stdlib XLSX writer.

Validates the produced file as a real OOXML package: it must open as a zip,
contain the required parts, and its worksheet must reference correctly escaped
shared strings (Korean text and XML-special characters).
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile

from heavycon_analyzer.export.xlsx_exporter import SHEET_NAME, export_xlsx, write_xlsx
from heavycon_analyzer.model import ExtractedField

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

EXPECTED_PARTS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/worksheets/sheet1.xml",
    "xl/sharedStrings.xml",
}


def _sample_fields() -> list[ExtractedField]:
    return [
        ExtractedField(
            box_no=5,
            english_label="Cargo",
            korean_label="화물",
            # value intentionally contains XML-special characters
            value="Steel & pipes <heavy> lift > 100t",
            raw_text="Cargo Steel & pipes",
            confidence=88.0,
        ),
        ExtractedField(
            box_no=2,
            english_label="Owners/Place of business",
            korean_label="용선주(Out)/선주",
            value="대한해운 주식회사",
            raw_text="Owners 대한해운",
            confidence=94.0,
        ),
    ]


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values = []
    for si in root.findall(f"{{{_MAIN_NS}}}si"):
        t = si.find(f"{{{_MAIN_NS}}}t")
        values.append(t.text if t is not None and t.text is not None else "")
    return values


def _cell_values(zf: zipfile.ZipFile) -> list[list[str]]:
    strings = _shared_strings(zf)
    root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    sheet_data = root.find(f"{{{_MAIN_NS}}}sheetData")
    assert sheet_data is not None
    rows: list[list[str]] = []
    for row in sheet_data.findall(f"{{{_MAIN_NS}}}row"):
        cells: list[str] = []
        for c in row.findall(f"{{{_MAIN_NS}}}c"):
            assert c.get("t") == "s", "cells should be shared-string typed"
            v = c.find(f"{{{_MAIN_NS}}}v")
            assert v is not None and v.text is not None
            cells.append(strings[int(v.text)])
        rows.append(cells)
    return rows


def test_output_is_valid_zip_with_expected_parts() -> None:
    data = write_xlsx(_sample_fields())
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert zf.testzip() is None
        names = set(zf.namelist())
        assert EXPECTED_PARTS.issubset(names)


def test_sheet_name_and_workbook_reference() -> None:
    data = write_xlsx(_sample_fields())
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        sheets = wb.find(f"{{{_MAIN_NS}}}sheets")
        assert sheets is not None
        sheet = sheets.find(f"{{{_MAIN_NS}}}sheet")
        assert sheet is not None
        assert sheet.get("name") == SHEET_NAME


def test_cell_values_and_escaping() -> None:
    data = write_xlsx(_sample_fields())
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        rows = _cell_values(zf)

    assert rows[0] == ["Box No", "English Label", "Korean Label", "Value"]
    # Korean text survived
    assert rows[2] == [
        "2",
        "Owners/Place of business",
        "용선주(Out)/선주",
        "대한해운 주식회사",
    ]
    # XML-special characters survived un-corrupted after XML parsing
    assert rows[1][3] == "Steel & pipes <heavy> lift > 100t"


def test_escaping_present_in_raw_xml() -> None:
    """The raw XML must contain escaped entities, not literal & < >."""
    data = write_xlsx(_sample_fields())
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        raw = zf.read("xl/sharedStrings.xml").decode("utf-8")
    assert "&amp;" in raw
    assert "&lt;heavy&gt;" in raw
    # A bare, unescaped ampersand must never appear.
    assert " & " not in raw


def test_export_xlsx_writes_openable_file(tmp_path) -> None:
    out = tmp_path / "out.xlsx"
    export_xlsx(_sample_fields(), str(out))
    with zipfile.ZipFile(out) as zf:
        assert EXPECTED_PARTS.issubset(set(zf.namelist()))


def test_model_tsv_parser_reads_fixture(tmp_path) -> None:
    """Sanity-check the TSV parser against the checked-in fixture."""
    from pathlib import Path

    from heavycon_analyzer.model import parse_tesseract_tsv

    fixture = Path(__file__).parent / "fixtures" / "sample_page.tsv"
    page = parse_tesseract_tsv(fixture.read_text(encoding="utf-8"))
    texts = [t.text for t in page.tokens]
    # Only level-5 word rows with text are kept.
    assert texts == ["Owners", "ACME", "Shipping", "Freight", "USD", "500,000"]
    assert all(t.conf >= 0 for t in page.tokens)
