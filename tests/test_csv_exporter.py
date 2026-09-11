"""Tests for the stdlib CSV exporter."""

from __future__ import annotations

import csv
import io

from heavycon_analyzer.export.csv_exporter import CSV_HEADER, export_csv, write_csv
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
            box_no=16,
            english_label="Freight",
            korean_label="운임",
            value="USD 500,000",
            raw_text="Freight USD 500,000",
            confidence=90.0,
        ),
    ]


def test_write_csv_has_bom_and_header() -> None:
    data = write_csv(_sample_fields())
    assert data.startswith(b"\xef\xbb\xbf"), "expected UTF-8 BOM"

    text = data.decode("utf-8-sig")
    reader = list(csv.reader(io.StringIO(text)))
    assert reader[0] == list(CSV_HEADER)


def test_korean_value_round_trips() -> None:
    data = write_csv(_sample_fields())
    text = data.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))

    # Header + 2 data rows
    assert len(rows) == 3
    assert rows[1] == ["2", "Owners/Place of business", "용선주(Out)/선주", "ACME 해운 주식회사"]
    assert rows[2] == ["16", "Freight", "운임", "USD 500,000"]


def test_export_csv_writes_file(tmp_path) -> None:
    out = tmp_path / "out.csv"
    export_csv(_sample_fields(), str(out))
    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert "용선주(Out)/선주" in raw.decode("utf-8-sig")
