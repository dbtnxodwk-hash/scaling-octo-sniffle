"""Headless GUI logic for heavycon_analyzer.

Everything in this module is a pure function or plain data with NO tkinter (and
no third-party) imports, so it can be unit-tested without a display or any OCR
engine. The tkinter widgets in :mod:`heavycon_analyzer.gui.app` delegate all of
their non-widget logic here.

Responsibilities:

* Map an :class:`~heavycon_analyzer.model.ExtractedField` list to the display
  rows shown in the ttk.Treeview (4 columns, box order preserved, empty values
  rendered as a blank string).
* Trigger CSV / XLSX export via the existing exporters, writing real files.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from ..export.csv_exporter import CSV_HEADER, export_csv
from ..export.xlsx_exporter import XLSX_HEADER, export_xlsx
from ..model import ExtractedField

__all__ = [
    "TABLE_COLUMNS",
    "field_to_row",
    "fields_to_rows",
    "export_fields_csv",
    "export_fields_xlsx",
]

# The four Treeview columns, in display order. These are the Korean headers the
# user sees in the window.
TABLE_COLUMNS: Sequence[str] = ("Box 번호", "항목(영문)", "항목(한글)", "값")


def field_to_row(field: ExtractedField) -> tuple[str, str, str, str]:
    """Map a single :class:`ExtractedField` to a 4-column display tuple.

    Columns: Box number, English label, Korean label, value. The value is
    rendered as-is; an empty/whitespace-only value becomes an empty string so
    the table cell shows blank rather than stray whitespace.
    """
    value = field.value if (field.value and field.value.strip()) else ""
    return (str(field.box_no), field.english_label, field.korean_label, value)


def fields_to_rows(fields: Iterable[ExtractedField]) -> list[tuple[str, str, str, str]]:
    """Map an ExtractedField list to Treeview rows, preserving input order.

    The pipeline already returns fields in box order (Box 1..30), so the order
    of ``fields`` is preserved verbatim here.
    """
    return [field_to_row(f) for f in fields]


def export_fields_csv(fields: Iterable[ExtractedField], path: str) -> str:
    """Write ``fields`` to ``path`` as CSV and return the path.

    Thin wrapper over :func:`heavycon_analyzer.export.csv_exporter.export_csv`
    so the GUI (and tests) have a single entry point for the CSV save action.
    ``fields`` is materialised first so it can be a one-shot iterator.
    """
    export_csv(list(fields), path)
    return path


def export_fields_xlsx(fields: Iterable[ExtractedField], path: str) -> str:
    """Write ``fields`` to ``path`` as XLSX and return the path.

    Thin wrapper over
    :func:`heavycon_analyzer.export.xlsx_exporter.export_xlsx`.
    """
    export_xlsx(list(fields), path)
    return path


# Re-exported so the app/tests can reference the exporter header row without
# reaching across packages; the CSV and XLSX headers are identical by design.
assert tuple(CSV_HEADER) == tuple(XLSX_HEADER)
