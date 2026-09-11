"""Core data model for heavycon_analyzer.

Pure standard-library dataclasses plus a Tesseract TSV parser. No third-party
imports so that fixtures can drive extraction/export tests fully offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "OcrToken",
    "OcrPage",
    "ExtractedField",
    "parse_tesseract_tsv",
]


@dataclass(frozen=True)
class OcrToken:
    """A single OCR token as produced by Tesseract's TSV output.

    Coordinates are in pixels relative to the top-left of the page image.
    ``conf`` is Tesseract's confidence (0-100); non-word rows report -1.
    """

    text: str
    left: int
    top: int
    width: int
    height: int
    conf: float
    page: int
    block: int
    par: int
    line: int
    word: int


@dataclass(frozen=True)
class OcrPage:
    """All word tokens recognised on a single page image."""

    page_index: int
    width: int
    height: int
    tokens: list[OcrToken] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractedField:
    """A single HEAVYCON PART I box value extracted from OCR output."""

    box_no: int
    english_label: str
    korean_label: str
    value: str
    raw_text: str
    confidence: float


# Standard Tesseract ``image_to_data``/TSV column order.
_TSV_COLUMNS = (
    "level",
    "page_num",
    "block_num",
    "par_num",
    "line_num",
    "word_num",
    "left",
    "top",
    "width",
    "height",
    "conf",
    "text",
)

# Tesseract level 5 == a recognised word. Lower levels are structural rows
# (page/block/paragraph/line) that carry no text.
_WORD_LEVEL = 5


def _to_int(raw: str, default: int = 0) -> int:
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


def _to_float(raw: str, default: float = -1.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def parse_tesseract_tsv(
    tsv_text: str,
    *,
    page_index: int = 0,
    page_width: int = 0,
    page_height: int = 0,
) -> OcrPage:
    """Parse Tesseract TSV text into an :class:`OcrPage`.

    The TSV has a header row followed by one row per structural element. Only
    ``level == 5`` (word) rows with non-empty text are kept as tokens. Blank
    lines and malformed rows are skipped so real Tesseract output and hand
    written fixtures both parse cleanly.
    """

    tokens: list[OcrToken] = []
    lines = tsv_text.splitlines()
    if not lines:
        return OcrPage(page_index=page_index, width=page_width, height=page_height, tokens=[])

    header = lines[0].split("\t")
    # Accept the canonical header; otherwise assume canonical column order.
    if [h.strip() for h in header] == list(_TSV_COLUMNS):
        data_lines = lines[1:]
    elif len(header) == len(_TSV_COLUMNS) and header[0].strip().isdigit():
        # No header row present; the first line is already data.
        data_lines = lines
    else:
        data_lines = lines[1:]

    for line in data_lines:
        if not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) < len(_TSV_COLUMNS):
            continue
        # cols may include trailing tab-split fragments; align to known columns.
        row = dict(zip(_TSV_COLUMNS, cols, strict=False))
        level = _to_int(row["level"], default=0)
        if level != _WORD_LEVEL:
            continue
        text = row["text"]
        if text.strip() == "":
            continue
        tokens.append(
            OcrToken(
                text=text,
                left=_to_int(row["left"]),
                top=_to_int(row["top"]),
                width=_to_int(row["width"]),
                height=_to_int(row["height"]),
                conf=_to_float(row["conf"]),
                page=_to_int(row["page_num"]),
                block=_to_int(row["block_num"]),
                par=_to_int(row["par_num"]),
                line=_to_int(row["line_num"]),
                word=_to_int(row["word_num"]),
            )
        )

    return OcrPage(
        page_index=page_index,
        width=page_width,
        height=page_height,
        tokens=tokens,
    )
