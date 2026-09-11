"""Minimal, valid .xlsx (OOXML) writer using only the standard library.

openpyxl is not installable offline, so this module builds a genuine
SpreadsheetML workbook from scratch with :mod:`zipfile` and hand-written XML.

It produces the required OOXML parts:

* ``[Content_Types].xml``
* ``_rels/.rels``
* ``xl/workbook.xml``
* ``xl/_rels/workbook.xml.rels``
* ``xl/worksheets/sheet1.xml``
* ``xl/sharedStrings.xml``

All string cells are stored via the shared-strings table (correctly indexed)
and every value is XML-escaped, so ``&``, ``<``, ``>`` and Korean text survive a
round trip. The output opens as a normal .xlsx in Excel/LibreOffice and as a
plain zip via :mod:`zipfile`.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable, Sequence

from ..model import ExtractedField

__all__ = [
    "SHEET_NAME",
    "XLSX_HEADER",
    "write_xlsx",
    "export_xlsx",
]

SHEET_NAME = "HEAVYCON"
XLSX_HEADER: Sequence[str] = ("Box No", "English Label", "Korean Label", "Value")

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels"'
    ' ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml"'
    ' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml"'
    ' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/sharedStrings.xml"'
    ' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
    "</Types>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1"'
    ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
    ' Target="xl/workbook.xml"/>'
    "</Relationships>"
)

_WORKBOOK_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1"'
    ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"'
    ' Target="worksheets/sheet1.xml"/>'
    '<Relationship Id="rId2"'
    ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings"'
    ' Target="sharedStrings.xml"/>'
    "</Relationships>"
)


def _escape(text: str) -> str:
    """XML-escape text content (order matters: ``&`` first)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(text: str) -> str:
    return _escape(text).replace('"', "&quot;")


def _column_letter(index: int) -> str:
    """1-based column index -> spreadsheet column letters (1 -> A, 27 -> AA)."""
    letters = ""
    while index > 0:
        index, rem = divmod(index - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def _workbook_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        f'<sheet name="{_escape_attr(SHEET_NAME)}" sheetId="1" r:id="rId1"/>'
        "</sheets>"
        "</workbook>"
    )


def _shared_strings_xml(strings: Sequence[str]) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        f' count="{len(strings)}" uniqueCount="{len(strings)}">',
    ]
    for s in strings:
        # xml:space="preserve" keeps leading/trailing whitespace intact.
        parts.append(f'<si><t xml:space="preserve">{_escape(s)}</t></si>')
    parts.append("</sst>")
    return "".join(parts)


def _sheet_xml(matrix: Sequence[Sequence[str]], string_index: dict[str, int]) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<sheetData>",
    ]
    for row_idx, row in enumerate(matrix, start=1):
        parts.append(f'<row r="{row_idx}">')
        for col_idx, cell in enumerate(row, start=1):
            ref = f"{_column_letter(col_idx)}{row_idx}"
            # Every cell is stored as a shared string (type "s"); the value is
            # the index into sharedStrings.xml.
            sidx = string_index[cell]
            parts.append(f'<c r="{ref}" t="s"><v>{sidx}</v></c>')
        parts.append("</row>")
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def _build_matrix(fields: Iterable[ExtractedField]) -> list[list[str]]:
    matrix: list[list[str]] = [list(XLSX_HEADER)]
    for f in fields:
        matrix.append([str(f.box_no), f.english_label, f.korean_label, f.value])
    return matrix


def write_xlsx(fields: Iterable[ExtractedField]) -> bytes:
    """Render ``fields`` to the bytes of a valid .xlsx workbook."""
    matrix = _build_matrix(fields)

    # Build a de-duplicated shared-strings table preserving first-seen order.
    string_index: dict[str, int] = {}
    ordered_strings: list[str] = []
    for row in matrix:
        for cell in row:
            if cell not in string_index:
                string_index[cell] = len(ordered_strings)
                ordered_strings.append(cell)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _ROOT_RELS)
        zf.writestr("xl/workbook.xml", _workbook_xml())
        zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        zf.writestr("xl/sharedStrings.xml", _shared_strings_xml(ordered_strings))
        zf.writestr("xl/worksheets/sheet1.xml", _sheet_xml(matrix, string_index))
    return buffer.getvalue()


def export_xlsx(fields: Iterable[ExtractedField], path: str) -> None:
    """Write ``fields`` to ``path`` as an .xlsx workbook."""
    data = write_xlsx(fields)
    with open(path, "wb") as fh:
        fh.write(data)
