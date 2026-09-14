"""Rule-based extraction of HEAVYCON 2007 PART I box values from OCR tokens.

This module is intentionally PURE (standard library only) so the whole
extraction pipeline is unit-testable offline against synthetic Tesseract TSV
fixtures -- no real Tesseract engine required.

Strategy (see :func:`extract_fields`):

1. Group OCR tokens into text lines per ``(page, block, par, line)`` ordered by
   ``left`` so we can reason about the printed form line by line.
2. Locate each box header by matching its box number token (e.g. ``16.``,
   tolerant of common OCR confusions such as ``l6.`` / ``I6.``) immediately
   followed by the box label words matched against ``anchor_patterns``.
3. Capture the value spatially: the tokens that sit inside the box region --
   below the header line and above the next box header in the same column, and
   to the left of the neighbouring column. When the layout is ambiguous we fall
   back to the trailing text on the header line itself.
4. Confidence is the mean Tesseract ``conf`` of the captured value tokens.

Box 30 (special provisions) is captured verbatim as multi-line raw text with
only whitespace normalisation -- never summarised.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .boxes import BoxDefinition
from .model import ExtractedField, OcrPage, OcrToken

__all__ = [
    "extract_fields",
    "normalize_whitespace",
    "collapse_spaces",
    "fix_line_break_hyphenation",
    "join_words",
]


# ---------------------------------------------------------------------------
# Normalisation helpers (pure functions).
# ---------------------------------------------------------------------------

# Characters commonly confused by OCR, mapped to a canonical digit so a box
# number like "l6." / "I6." / "S." still matches the intended "16." / "5.".
_OCR_DIGIT_CONFUSIONS = str.maketrans(
    {
        "O": "0",
        "o": "0",
        "l": "1",
        "I": "1",
        "i": "1",
        "|": "1",
        "S": "5",
        "s": "5",
        "B": "8",
        "Z": "2",
        "z": "2",
        "g": "9",
    }
)


def collapse_spaces(text: str) -> str:
    """Collapse runs of whitespace into single spaces and strip the ends."""
    return re.sub(r"\s+", " ", text).strip()


def fix_line_break_hyphenation(text: str) -> str:
    """Join words split across a line break by a trailing hyphen.

    ``"demob-\\nilisation"`` -> ``"demobilisation"``. Only a hyphen directly
    before a newline is treated as hyphenation; genuine hyphenated compounds on
    a single line are left untouched.
    """
    return re.sub(r"-\s*\n\s*", "", text)


def normalize_whitespace(text: str) -> str:
    """Normalise whitespace while preserving line structure.

    Trailing/leading spaces are trimmed per line, runs of spaces/tabs within a
    line collapse to one, and runs of blank lines collapse to a single newline.
    Used for the Box 30 raw text so multi-line content is preserved verbatim
    apart from whitespace tidy-up.
    """
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    # Drop blank lines entirely so runs of blank lines collapse to a single
    # newline separator between content lines.
    out = [ln for ln in lines if ln != ""]
    return "\n".join(out)


def join_words(tokens: list[OcrToken]) -> str:
    """Join token texts with single spaces after collapsing whitespace."""
    return collapse_spaces(" ".join(t.text for t in tokens))


# ---------------------------------------------------------------------------
# Line reconstruction.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Line:
    """A reconstructed OCR text line grouped from word tokens."""

    page_index: int
    block: int
    par: int
    line: int
    tokens: tuple[OcrToken, ...]

    @property
    def left(self) -> int:
        return min(t.left for t in self.tokens)

    @property
    def right(self) -> int:
        return max(t.left + t.width for t in self.tokens)

    @property
    def top(self) -> int:
        return min(t.top for t in self.tokens)

    @property
    def bottom(self) -> int:
        return max(t.top + t.height for t in self.tokens)

    @property
    def vcenter(self) -> float:
        return (self.top + self.bottom) / 2.0

    @property
    def text(self) -> str:
        return join_words(list(self.tokens))


def _build_lines(page: OcrPage) -> list[_Line]:
    """Group a page's tokens into text lines ordered top-to-bottom, left-to-right."""
    groups: dict[tuple[int, int, int], list[OcrToken]] = {}
    for tok in page.tokens:
        key = (tok.block, tok.par, tok.line)
        groups.setdefault(key, []).append(tok)

    lines: list[_Line] = []
    for (block, par, line), toks in groups.items():
        ordered = tuple(sorted(toks, key=lambda t: t.left))
        lines.append(
            _Line(
                page_index=page.page_index,
                block=block,
                par=par,
                line=line,
                tokens=ordered,
            )
        )
    lines.sort(key=lambda ln: (ln.top, ln.left))
    return lines


# ---------------------------------------------------------------------------
# Header matching.
# ---------------------------------------------------------------------------

_BOX_NO_RE = re.compile(r"^\(?([0-9OoIlL|SsBZzg]{1,2})\s*[.)\-:]?\)?$")

# A leading box-number prefix glued onto the first label word, e.g. real
# Tesseract emits ``16.Freight`` (or the OCR-confused ``l6.Freight``) as a
# single token in tight form cells. We peel ``<digits><separator>`` off the
# front so the number can be matched and the remainder treated as a label
# token. A separator ([.)\-:]) is required so we do not accidentally split a
# genuine value token like ``60days`` -- box numbers on the form are always
# printed with a trailing punctuation mark.
_GLUED_BOX_NO_RE = re.compile(r"^\(?([0-9OoIlL|SsBZzg]{1,2})[.)\-:]\)?(.+)$")


def _normalize_box_number_token(text: str) -> int | None:
    """Return the box number encoded by a leading token, tolerant of OCR noise.

    Accepts forms like ``16.``, ``16)``, ``(16)``, ``16``. Also repairs common
    OCR letter/digit confusions so ``l6.`` -> 16 and ``S.`` -> 5.
    """
    stripped = text.strip()
    match = _BOX_NO_RE.match(stripped)
    if not match:
        return None
    digits = match.group(1).translate(_OCR_DIGIT_CONFUSIONS)
    if not digits.isdigit():
        return None
    try:
        value = int(digits)
    except ValueError:
        return None
    if 1 <= value <= 99:
        return value
    return None


def _split_glued_box_number(text: str) -> tuple[int, str] | None:
    """Split a merged ``<number><sep><label>`` token, e.g. ``16.Freight``.

    Returns ``(box_no, remainder_label)`` when the token starts with a
    box-number prefix followed by a separator and then further label text, else
    ``None``. The number half runs through the same OCR-confusion repair as a
    standalone number token so ``l6.Freight`` -> ``(16, "Freight")``.
    """
    stripped = text.strip()
    match = _GLUED_BOX_NO_RE.match(stripped)
    if not match:
        return None
    remainder = match.group(2).strip()
    if not remainder:
        return None
    box_no = _normalize_box_number_token(match.group(1) + ".")
    if box_no is None:
        return None
    return box_no, remainder


def _line_header_number_and_label(line: _Line) -> tuple[int, str] | None:
    """Return ``(box_no, label_text)`` for a line's leading header token.

    Handles both the clean layout where the box number is its own token
    (``16.`` then ``Freight``) and the common real-OCR case where the number is
    glued onto the first label word (``16.Freight`` -> ``(16, "Freight ...")``).
    Returns ``None`` when the first token is not a box-number header.
    """
    if not line.tokens:
        return None
    first = line.tokens[0].text
    first_no = _normalize_box_number_token(first)
    if first_no is not None:
        # Clean case: number is a standalone token; label follows.
        label_text = join_words(list(line.tokens[1:]))
        return first_no, label_text
    glued = _split_glued_box_number(first)
    if glued is not None:
        box_no, remainder = glued
        rest = join_words(list(line.tokens[1:]))
        label_text = f"{remainder} {rest}".strip() if rest else remainder
        return box_no, label_text
    return None


def _line_matches_box(line: _Line, box: BoxDefinition) -> bool:
    """Return True if ``line`` looks like the header for ``box``.

    A header must (a) start with the box number token (OCR-tolerant, including
    a number glued onto the first label word) and (b) contain label words
    matching one of the box's anchor patterns on the same line.
    """
    # Issue 7 (loose anchors) note: several anchors are deliberately loose
    # single-word patterns (\bcargo\b, \bfreight\b, \bnotices?\b, \bcanal\b) so
    # OCR label variants still match. They are safe ONLY because a matching
    # leading box-number token is ALSO required (the number gate below). The
    # glued-token splitter added for issue 1 preserves this gate: it only peels
    # a prefix that is itself a valid box number followed by a separator, so a
    # body word can never masquerade as a header. Do not relax the number gate.
    header = _line_header_number_and_label(line)
    if header is None:
        return False
    box_no, label_text = header
    if box_no != box.box_no:
        return False
    if not label_text:
        return False
    for pat in box.compiled_patterns():
        if pat.search(label_text):
            return True
    return False


# ---------------------------------------------------------------------------
# Value capture.
# ---------------------------------------------------------------------------


def _same_column(header: _Line, candidate: _Line, page_width: int) -> bool:
    """Heuristic: is ``candidate`` in the same box column as ``header``?

    A two-column grid splits the page near the middle. A candidate belongs to
    the header's column when its horizontal centre is on the same side of the
    page mid-line as the header's left edge (with a tolerance so values that
    are indented under the header still count).
    """
    if page_width <= 0:
        # No page geometry: treat everything as a single column.
        return True
    mid = page_width / 2.0
    header_left = header.left
    cand_center = (candidate.left + candidate.right) / 2.0
    header_side_right = header_left >= mid
    cand_side_right = cand_center >= mid
    if header_side_right == cand_side_right:
        return True
    # Tolerance: a value slightly crossing the mid-line but clearly under the
    # header still belongs to it.
    return abs(cand_center - header_left) <= page_width * 0.08


def _header_body_text(header: _Line, box: BoxDefinition) -> str:
    """The header line's text after the box-number token (label + inline value).

    Uses :func:`_line_header_number_and_label` so it works whether the number
    is a standalone token (``16. Freight USD 5,000``) or glued to the first
    label word (``16.Freight USD 5,000``).
    """
    header_info = _line_header_number_and_label(header)
    if header_info is None:
        return ""
    _box_no, label_text = header_info
    return label_text


# A token that "looks like a value" rather than a label word: currency codes,
# money amounts, counts, dates, percentages, etc. Used to cut the label span at
# the first value-looking token so inline values survive the same-line fallback.
_VALUE_LOOKING_RE = re.compile(
    r"""
    ^(?:
        \$?[0-9]                       # starts with a digit (optionally $): 5,000  72  100%
      | (?:USD|EUR|GBP|JPY|KRW|CHF|CAD|AUD|SGD)$   # bare currency code
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _looks_like_value_word(word: str) -> bool:
    """True when a body word looks like the start of an inline value.

    Currency codes (``USD``), amounts (``2,500,000``), counts (``72``) and
    percentages (``100%``) mark where the printed label ends and the filled-in
    value begins on a single header line.
    """
    return bool(_VALUE_LOOKING_RE.match(word.strip()))


def _label_words(body_words: list[str], box: BoxDefinition) -> int:
    """Number of leading ``body_words`` that make up the printed label.

    Fix for the dead greedy fallback (issue 2): rather than growing the label
    as long as *any* anchor still ``search``-matched -- which let value words
    count as label and returned an empty value -- we anchor the label at the
    START of the body and stop at the first value-looking word. Concretely we
    take the longest leading run of words such that (a) no word in the run looks
    like a value and (b) the joined prefix ``match``-es an anchor from position
    0, then extend past any further non-value words that keep an anchor
    ``search``-matching within the label region. Value words (``USD 5,000``)
    are never absorbed, so ``Freight USD 5,000`` yields a label span of 1.
    """
    patterns = box.compiled_patterns()
    # First, find the shortest anchored prefix that matches from the start.
    anchored = 0
    for count in range(1, len(body_words) + 1):
        if _looks_like_value_word(body_words[count - 1]):
            break
        prefix = collapse_spaces(" ".join(body_words[:count]))
        if any(p.match(prefix) for p in patterns):
            anchored = count
            break
    if anchored == 0:
        return 0
    # Then extend the label across further NON-value words (multi-word labels
    # such as "Additional clauses covering special provisions" where later
    # words are not part of the same anchor match). Stop at the first
    # value-looking word.
    span = anchored
    while span < len(body_words) and not _looks_like_value_word(body_words[span]):
        span += 1
    return span


def _header_trailing_text(header: _Line, box: BoxDefinition) -> str:
    """Inline value on the header line, after the label (same-line fallback).

    The label is matched at the START of the body and stopped at the first
    value-looking token so an inline value survives: ``16. Freight USD 5,000``
    -> ``USD 5,000``. This is the fix for the previously-dead greedy fallback
    which counted the value words as part of the label. See :func:`_label_words`.
    """
    body = _header_body_text(header, box)
    if not body:
        return ""
    words = body.split()
    label_count = _label_words(words, box)
    if label_count <= 0 or label_count >= len(words):
        return ""
    return collapse_spaces(" ".join(words[label_count:]))


def _header_trailing_conf(header: _Line, box: BoxDefinition) -> float:
    """Mean confidence of the inline-value tokens on the header line.

    Mirrors :func:`_header_trailing_text` token-wise: it takes the shortest
    suffix of the header tokens whose joined text ends with the trailing value
    and averages the confidence of those tokens.
    """
    trailing = _header_trailing_text(header, box)
    if not trailing:
        return 0.0
    trailing_norm = collapse_spaces(trailing)
    tokens = list(header.tokens)
    for start in range(len(tokens)):
        suffix = tokens[start:]
        joined = collapse_spaces(join_words(suffix))
        if joined.endswith(trailing_norm):
            return _mean_conf(suffix)
    return _mean_conf(tokens)


def _value_lines_below(
    header: _Line,
    lines: list[_Line],
    header_index: int,
    next_header_top: int | None,
    page_width: int,
) -> list[_Line]:
    """Lines that fall inside the box region below the header.

    Issue 6 (cross-page region bleed) note: capture is bounded (a) horizontally
    by ``_same_column`` and (b) vertically by ``next_header_top`` -- the next
    box header in the same column. When a box is the LAST in its column there is
    no following header, so capture runs to the page bottom. This is intentional
    and correct for a single-page HEAVYCON 2007 PART I (Box 30 special
    provisions is deliberately greedy and captures its full multi-line block).
    ``extract_fields`` already filters ``lines`` to the header's own page, so a
    box never bleeds into a following page. A hypothetical multi-page PART I
    variant with footer text under the last box could over-capture, but the 2007
    standard PART I is one page, so no explicit page-bottom clamp is added here.
    """
    captured: list[_Line] = []
    for other in lines[header_index + 1 :]:
        if other.top <= header.bottom - 1:
            # Not actually below the header baseline.
            continue
        if next_header_top is not None and other.top >= next_header_top:
            break
        if not _same_column(header, other, page_width):
            continue
        captured.append(other)
    return captured


def _mean_conf(tokens: list[OcrToken]) -> float:
    confs = [t.conf for t in tokens if t.conf >= 0]
    if not confs:
        return 0.0
    return round(sum(confs) / len(confs), 2)


def _find_next_header_top(
    header: _Line,
    header_lines: list[tuple[int, _Line]],
    page_width: int,
) -> int | None:
    """Top coordinate of the next box header below ``header`` in its column."""
    candidates = [
        hl.top
        for _, hl in header_lines
        if hl.top > header.top and _same_column(header, hl, page_width)
    ]
    if not candidates:
        return None
    return min(candidates)


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def _empty_field(box: BoxDefinition) -> ExtractedField:
    return ExtractedField(
        box_no=box.box_no,
        english_label=box.english_label,
        korean_label=box.korean_label,
        value="",
        raw_text="",
        confidence=0.0,
    )


def _locate_header(lines: list[_Line], box: BoxDefinition) -> int | None:
    """Return the index of the first line matching the box header, else None."""
    for idx, line in enumerate(lines):
        if _line_matches_box(line, box):
            return idx
    return None


def extract_fields(
    pages: list[OcrPage],
    boxes: list[BoxDefinition],
) -> list[ExtractedField]:
    """Extract one :class:`ExtractedField` per box definition.

    Missing boxes never raise: they yield an empty value with confidence 0.0 so
    the resulting table always shows every target row. The result order matches
    the order of ``boxes``.
    """
    # Reconstruct lines for every page and remember which page each line is on.
    all_lines: list[_Line] = []
    page_by_index: dict[int, OcrPage] = {}
    for page in pages:
        page_by_index[page.page_index] = page
        all_lines.extend(_build_lines(page))
    all_lines.sort(key=lambda ln: (ln.page_index, ln.top, ln.left))

    def _page_width(line: _Line) -> int:
        page = page_by_index.get(line.page_index)
        return page.width if page is not None else 0

    # Pre-compute all header lines so region boundaries can reference any box.
    header_lines: list[tuple[int, _Line]] = []
    for box in boxes:
        idx = _locate_header(all_lines, box)
        if idx is not None:
            header_lines.append((box.box_no, all_lines[idx]))

    results: list[ExtractedField] = []
    for box in boxes:
        header_idx = _locate_header(all_lines, box)
        if header_idx is None:
            results.append(_empty_field(box))
            continue

        header = all_lines[header_idx]
        page_width = _page_width(header)

        # Boundaries: the next header below this one in the same column, and
        # only lines on the same page participate in this box's region.
        same_page_lines = [ln for ln in all_lines if ln.page_index == header.page_index]
        same_page_header_idx = same_page_lines.index(header)
        same_page_headers = [
            (no, hl) for no, hl in header_lines if hl.page_index == header.page_index
        ]
        next_top = _find_next_header_top(header, same_page_headers, page_width)

        value_lines = _value_lines_below(
            header,
            same_page_lines,
            same_page_header_idx,
            next_top,
            page_width,
        )
        value_tokens: list[OcrToken] = [t for ln in value_lines for t in ln.tokens]

        if box.raw_text_only:
            raw = normalize_whitespace("\n".join(ln.text for ln in value_lines))
            trailing = _header_trailing_text(header, box)
            if trailing:
                raw = normalize_whitespace(trailing + "\n" + raw) if raw else trailing
            conf = _mean_conf(value_tokens) if value_tokens else _mean_conf(list(header.tokens))
            results.append(
                ExtractedField(
                    box_no=box.box_no,
                    english_label=box.english_label,
                    korean_label=box.korean_label,
                    value=raw,
                    raw_text=raw,
                    confidence=conf,
                )
            )
            continue

        raw_joined = " ".join(ln.text for ln in value_lines)
        value = collapse_spaces(fix_line_break_hyphenation(raw_joined))

        if not value:
            # Fall back to the inline value on the header line itself.
            trailing = _header_trailing_text(header, box)
            value = collapse_spaces(trailing)
            conf = _header_trailing_conf(header, box) if value else 0.0
        else:
            conf = _mean_conf(value_tokens)

        results.append(
            ExtractedField(
                box_no=box.box_no,
                english_label=box.english_label,
                korean_label=box.korean_label,
                value=value,
                raw_text=value,
                confidence=conf,
            )
        )

    return results
