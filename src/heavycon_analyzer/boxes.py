"""HEAVYCON 2007 PART I box definitions.

BIMCO HEAVYCON 2007 (Standard Heavy Lift Charter Party) has a fixed PART I
"box layout" (Box 1-30). Extraction is rule-based, anchored on the box number
and label text, so these definitions are the single source of truth for what
we look for and how we present it.

Each :class:`BoxDefinition` carries the English label, a Korean label (as used
in the user's requirements), and a list of ``anchor_patterns`` -- case-
insensitive regex fragments matched against OCR text to locate the box header.

IMPORTANT -- label accuracy:
The box NUMBERS below for the fields the user explicitly named are fixed by the
task requirements (see FEAT-001) and are treated as authoritative. For a few
boxes the exact printed HEAVYCON 2007 wording is not 100% certain from memory;
those definitions carry a ``# TODO(confirm-label)`` comment. In every such case
we use the best-known standard HEAVYCON label -- we never invent a box number
for a named field. These should be confirmed against an original HEAVYCON 2007
PART I form.

Review issue 3 (unverified labels 11,12,13,14,17,24-29): deliberately NOT
"fixed" here. Confirming the exact printed 2007 wording requires an original
copyrighted BIMCO PART I form, which is not available in this offline
environment, and guessing a different string would be no more authoritative
than the current best-known wording. The uncertainty is disclosed honestly via
the ``# TODO(confirm-label)`` markers below. Crucially this does not affect
extraction correctness: header matching keys on the box NUMBER first (see
``extractor._line_matches_box``), so an imperfect label only weakens a secondary
anchor -- it never yields a wrong extraction. The box numbers for every
user-named field are authoritative and must not change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = [
    "BoxDefinition",
    "BOX_DEFINITIONS",
    "SPECIAL_PROVISIONS_BOX_NO",
    "get_box",
    "iter_boxes",
]

# Box 30 holds the "additional clauses covering special provisions". Its value
# is extracted as RAW TEXT ONLY -- no summarisation (per requirements).
SPECIAL_PROVISIONS_BOX_NO = 30


@dataclass(frozen=True)
class BoxDefinition:
    """Definition of one HEAVYCON 2007 PART I box.

    Attributes:
        box_no: The PART I box number (1-30).
        english_label: The English label as printed on the form.
        korean_label: Korean label used in the app UI / requirements.
        anchor_patterns: Case-insensitive regex fragments used to locate the
            box header within OCR text.
        raw_text_only: If True, the box value is presented verbatim with no
            normalisation/summarisation (used for Box 30 special provisions).
    """

    box_no: int
    english_label: str
    korean_label: str
    anchor_patterns: list[str] = field(default_factory=list)
    raw_text_only: bool = False

    def compiled_patterns(self) -> list[re.Pattern[str]]:
        """Return the anchor patterns compiled as case-insensitive regexes."""
        return [re.compile(p, re.IGNORECASE) for p in self.anchor_patterns]


# ---------------------------------------------------------------------------
# HEAVYCON 2007 PART I -- Box 1-30.
#
# The numbering and English wording follow the standard BIMCO HEAVYCON 2007
# PART I layout. Boxes flagged with TODO(confirm-label) should be verified
# against an original form; their box NUMBERS for user-named fields are fixed.
# ---------------------------------------------------------------------------
BOX_DEFINITIONS: list[BoxDefinition] = [
    BoxDefinition(
        box_no=1,
        english_label="Place and date",
        korean_label="장소 및 일자",
        anchor_patterns=[r"place\s+and\s+date"],
    ),
    BoxDefinition(
        box_no=2,
        english_label="Owners/Place of business",
        korean_label="용선주(Out)/선주",
        anchor_patterns=[r"owners?\b.*place\s+of\s+business", r"\bowners?\b"],
    ),
    BoxDefinition(
        box_no=3,
        english_label="Charterers/Place of business",
        korean_label="용선주(In)/용선자",
        anchor_patterns=[r"charterers?\b.*place\s+of\s+business", r"\bcharterers?\b"],
    ),
    BoxDefinition(
        box_no=4,
        english_label="Vessel's name",
        korean_label="선박",
        anchor_patterns=[r"vessel'?s?\s+name", r"\bvessel\b"],
    ),
    BoxDefinition(
        box_no=5,
        english_label="Cargo",
        korean_label="화물",
        anchor_patterns=[r"\bcargo\b"],
    ),
    BoxDefinition(
        box_no=6,
        english_label="Loading port or place",
        korean_label="선적지",
        anchor_patterns=[r"loading\s+port\s+or\s+place", r"loading\s+port", r"port\s+of\s+loading"],
    ),
    BoxDefinition(
        box_no=7,
        english_label="Discharging port or place",
        korean_label="양하지",
        anchor_patterns=[
            r"discharging\s+port\s+or\s+place",
            r"discharging\s+port",
            r"port\s+of\s+discharge",
        ],
    ),
    BoxDefinition(
        box_no=8,
        english_label="Loading method",
        korean_label="선적방식",
        anchor_patterns=[r"loading\s+method", r"method\s+of\s+loading"],
    ),
    BoxDefinition(
        box_no=9,
        english_label="Discharging method",
        korean_label="양하방식",
        anchor_patterns=[r"discharging\s+method", r"method\s+of\s+discharg"],
    ),
    BoxDefinition(
        box_no=10,
        english_label="The Period",
        korean_label="기간",
        anchor_patterns=[r"the\s+period", r"\bperiod\b"],
    ),
    BoxDefinition(
        box_no=11,
        english_label="Notification schedule by the Charterers",
        korean_label="일정통지(용선주)",
        # TODO(confirm-label): exact HEAVYCON 2007 wording for the Charterers'
        # notification-schedule box; box number fixed to 11 per requirements.
        anchor_patterns=[
            r"notification\s+schedule.*charterers?",
            r"charterers?.*notification\s+schedule",
            r"notification\s+schedule",
        ],
    ),
    BoxDefinition(
        box_no=12,
        english_label="Loading schedule to be provided by the Vessel",
        korean_label="선적일정(선박)",
        # TODO(confirm-label): loading-schedule notice box provided by the
        # Vessel; box number fixed to 12 per requirements.
        anchor_patterns=[
            r"loading\s+schedule.*vessel",
            r"vessel.*loading\s+schedule",
            r"loading\s+schedule",
        ],
    ),
    BoxDefinition(
        box_no=13,
        english_label="Discharging schedule to be provided by the Vessel",
        korean_label="양하일정(선박)",
        # TODO(confirm-label): discharging-schedule notice box provided by the
        # Vessel; box number fixed to 13 per requirements.
        anchor_patterns=[
            r"discharging\s+schedule.*vessel",
            r"vessel.*discharging\s+schedule",
            r"discharging\s+schedule",
        ],
    ),
    BoxDefinition(
        box_no=14,
        english_label="Cancelling date",
        korean_label="해약기일",
        # TODO(confirm-label): Box 14 wording; not a user-named field.
        anchor_patterns=[r"cancelling\s+date", r"canceling\s+date"],
    ),
    BoxDefinition(
        box_no=15,
        english_label="Marine Warranty Surveyor and transportation approval",
        korean_label="MWS & 승인",
        anchor_patterns=[
            r"marine\s+warranty\s+surveyor",
            r"\bmws\b",
            r"transportation\s+approval",
        ],
    ),
    BoxDefinition(
        box_no=16,
        english_label="Freight",
        korean_label="운임",
        anchor_patterns=[r"\bfreight\b"],
    ),
    BoxDefinition(
        box_no=17,
        english_label="Freight payment and bank details (Payment terms)",
        korean_label="운임수령/Payment terms",
        # TODO(confirm-label): exact split/wording of the freight payment /
        # bank details box; box number fixed to 17 per requirements.
        anchor_patterns=[
            r"freight\s+payment",
            r"payment\s+terms",
            r"bank\s+details",
            r"payment\b",
        ],
    ),
    BoxDefinition(
        box_no=18,
        english_label="Free time",
        korean_label="프리타임",
        anchor_patterns=[r"free\s+time", r"\bfreetime\b"],
    ),
    BoxDefinition(
        box_no=19,
        english_label="Demurrage rate per day",
        korean_label="디머리지",
        anchor_patterns=[r"demurrage\s+rate", r"\bdemurrage\b"],
    ),
    BoxDefinition(
        box_no=20,
        english_label="Mobilisation charge",
        korean_label="몹디몹 비용(Mob)",
        anchor_patterns=[r"mobilis?ation\s+charge", r"mobilis?ation"],
    ),
    BoxDefinition(
        box_no=21,
        english_label="Demobilisation charge",
        korean_label="몹디몹 비용(Demob)",
        anchor_patterns=[r"demobilis?ation\s+charge", r"demobilis?ation"],
    ),
    BoxDefinition(
        box_no=22,
        english_label="Canal transit costs",
        korean_label="운하통항비",
        anchor_patterns=[r"canal\s+transit", r"canal\s+dues", r"\bcanal\b"],
    ),
    BoxDefinition(
        box_no=23,
        english_label="Bunker escalation",
        korean_label="벙커 연동",
        anchor_patterns=[r"bunker\s+escalation", r"bunker\s+price", r"\bbunker\b"],
    ),
    BoxDefinition(
        box_no=24,
        english_label="Insurance",
        korean_label="보험",
        # TODO(confirm-label): Box 24 wording; not a user-named field.
        anchor_patterns=[r"\binsurance\b"],
    ),
    BoxDefinition(
        box_no=25,
        english_label="Law and arbitration",
        korean_label="준거법 및 중재",
        # TODO(confirm-label): Box 25 wording; not a user-named field.
        anchor_patterns=[r"law\s+and\s+arbitration", r"arbitration"],
    ),
    BoxDefinition(
        box_no=26,
        english_label="Brokerage commission and to whom payable",
        korean_label="중개수수료",
        # TODO(confirm-label): Box 26 wording; not a user-named field.
        anchor_patterns=[r"brokerage\s+commission", r"brokerage"],
    ),
    BoxDefinition(
        box_no=27,
        english_label="General Average to be adjusted at",
        korean_label="공동해손 정산지",
        # TODO(confirm-label): Box 27 wording; not a user-named field.
        anchor_patterns=[r"general\s+average"],
    ),
    BoxDefinition(
        box_no=28,
        english_label="War risk insurance premium",
        korean_label="전쟁위험 보험료",
        # TODO(confirm-label): Box 28 wording; not a user-named field.
        anchor_patterns=[r"war\s+risk", r"war\s+risks?\s+insurance"],
    ),
    BoxDefinition(
        box_no=29,
        english_label="Notices",
        korean_label="통지처",
        # TODO(confirm-label): Box 29 wording; not a user-named field.
        anchor_patterns=[r"\bnotices?\b"],
    ),
    BoxDefinition(
        box_no=SPECIAL_PROVISIONS_BOX_NO,
        english_label="Numbers of additional clauses covering special provisions",
        korean_label="특수조항",
        anchor_patterns=[
            r"additional\s+clauses",
            r"special\s+provisions?",
            r"numbers?\s+of\s+additional\s+clauses",
        ],
        raw_text_only=True,
    ),
]


_BOX_BY_NO: dict[int, BoxDefinition] = {b.box_no: b for b in BOX_DEFINITIONS}


def get_box(box_no: int) -> BoxDefinition:
    """Return the :class:`BoxDefinition` for ``box_no`` or raise ``KeyError``."""
    return _BOX_BY_NO[box_no]


def iter_boxes() -> list[BoxDefinition]:
    """Return the box definitions ordered by box number."""
    return list(BOX_DEFINITIONS)
