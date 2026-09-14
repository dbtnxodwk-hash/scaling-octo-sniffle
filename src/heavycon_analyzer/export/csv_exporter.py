"""CSV export using the standard-library :mod:`csv` module.

Writes a UTF-8 file with a BOM so Microsoft Excel opens Korean text correctly.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence

from ..model import ExtractedField

__all__ = ["CSV_HEADER", "write_csv", "export_csv"]

CSV_HEADER: Sequence[str] = ("Box No", "English Label", "Korean Label", "Value")


def _rows(fields: Iterable[ExtractedField]) -> list[list[str]]:
    rows: list[list[str]] = [list(CSV_HEADER)]
    for f in fields:
        rows.append([str(f.box_no), f.english_label, f.korean_label, f.value])
    return rows


def write_csv(fields: Iterable[ExtractedField]) -> bytes:
    """Render ``fields`` to CSV bytes (UTF-8 with BOM)."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    for row in _rows(fields):
        writer.writerow(row)
    # utf-8-sig prepends the BOM so Excel detects UTF-8.
    return buffer.getvalue().encode("utf-8-sig")


def export_csv(fields: Iterable[ExtractedField], path: str) -> None:
    """Write ``fields`` to ``path`` as a UTF-8-BOM CSV file."""
    data = write_csv(fields)
    with open(path, "wb") as fh:
        fh.write(data)
