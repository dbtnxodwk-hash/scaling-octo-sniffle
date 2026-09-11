"""Coverage tests for the HEAVYCON 2007 PART I box definitions."""

from __future__ import annotations

from heavycon_analyzer.boxes import (
    BOX_DEFINITIONS,
    SPECIAL_PROVISIONS_BOX_NO,
    get_box,
    iter_boxes,
)

# The user-named fields mapped to their required box numbers (FEAT-001 step 4).
REQUIRED_FIELDS = {
    2: "용선주(Out)/선주",
    3: "용선주(In)/용선자",
    4: "선박",
    5: "화물",
    6: "선적지",
    7: "양하지",
    8: "선적방식",
    9: "양하방식",
    10: "기간",
    11: "일정통지(용선주)",
    12: "선적일정(선박)",
    13: "양하일정(선박)",
    15: "MWS & 승인",
    16: "운임",
    17: "운임수령/Payment terms",
    18: "프리타임",
    19: "디머리지",
    20: "몹디몹 비용(Mob)",
    21: "몹디몹 비용(Demob)",
    22: "운하통항비",
    23: "벙커 연동",
    30: "특수조항",
}


def test_every_required_field_present_with_correct_box_number() -> None:
    for box_no, korean_label in REQUIRED_FIELDS.items():
        box = get_box(box_no)
        assert box.box_no == box_no
        assert (
            box.korean_label == korean_label
        ), f"Box {box_no} korean_label mismatch: {box.korean_label!r}"


def test_all_boxes_have_nonempty_labels_and_anchors() -> None:
    for box in BOX_DEFINITIONS:
        assert box.english_label.strip(), f"Box {box.box_no} has empty english_label"
        assert box.korean_label.strip(), f"Box {box.box_no} has empty korean_label"
        assert box.anchor_patterns, f"Box {box.box_no} has no anchor patterns"
        # anchor patterns must compile as regexes
        assert box.compiled_patterns()


def test_box_numbers_unique_and_ordered() -> None:
    numbers = [b.box_no for b in BOX_DEFINITIONS]
    assert len(numbers) == len(set(numbers)), "duplicate box numbers"
    assert numbers == sorted(numbers), "box numbers not in ascending order"


def test_covers_boxes_1_through_30() -> None:
    numbers = {b.box_no for b in BOX_DEFINITIONS}
    assert numbers == set(range(1, 31))


def test_special_provisions_is_raw_text_only() -> None:
    box = get_box(SPECIAL_PROVISIONS_BOX_NO)
    assert box.raw_text_only is True
    assert box.korean_label == "특수조항"


def test_iter_boxes_returns_copy() -> None:
    first = iter_boxes()
    first.clear()
    assert len(iter_boxes()) == 30
