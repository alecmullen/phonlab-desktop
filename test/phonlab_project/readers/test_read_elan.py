from pathlib import Path

import pytest

from phonlab_project.readers.read_tiers import read_tiers

HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<ANNOTATION_DOCUMENT FORMAT="3.0" VERSION="3.0">
<HEADER MEDIA_FILE="" TIME_UNITS="milliseconds"></HEADER>
<TIME_ORDER>
{slots}
</TIME_ORDER>
"""

LINGUISTIC_TYPES = """
<LINGUISTIC_TYPE LINGUISTIC_TYPE_ID="default-lt" TIME_ALIGNABLE="true"/>
<LINGUISTIC_TYPE CONSTRAINTS="Symbolic_Association" LINGUISTIC_TYPE_ID="assoc"
    TIME_ALIGNABLE="false"/>
<LINGUISTIC_TYPE CONSTRAINTS="Symbolic_Subdivision" LINGUISTIC_TYPE_ID="subdiv"
    TIME_ALIGNABLE="false"/>
"""


def slot(slot_id: str, value: int | None) -> str:
    attr = "" if value is None else f' TIME_VALUE="{value}"'
    return f'<TIME_SLOT TIME_SLOT_ID="{slot_id}"{attr}/>'


def alignable(ann_id: str, begin: str, end: str, text: str) -> str:
    return (
        f'<ANNOTATION><ALIGNABLE_ANNOTATION ANNOTATION_ID="{ann_id}" '
        f'TIME_SLOT_REF1="{begin}" TIME_SLOT_REF2="{end}">'
        f"<ANNOTATION_VALUE>{text}</ANNOTATION_VALUE></ALIGNABLE_ANNOTATION></ANNOTATION>"
    )


def reference(ann_id: str, parent: str, text: str, previous: str | None = None) -> str:
    chain = "" if previous is None else f' PREVIOUS_ANNOTATION="{previous}"'
    return (
        f'<ANNOTATION><REF_ANNOTATION ANNOTATION_ID="{ann_id}" '
        f'ANNOTATION_REF="{parent}"{chain}>'
        f"<ANNOTATION_VALUE>{text}</ANNOTATION_VALUE></REF_ANNOTATION></ANNOTATION>"
    )


def write_eaf(
    tmp_path: Path, tiers: str, slots: dict[str, int | None] | None = None
) -> str:
    slots = slots or {"ts1": 500, "ts2": 1500, "ts3": 3000}
    content = HEADER.format(slots="\n".join(slot(k, v) for k, v in slots.items()))
    path = tmp_path / "a.eaf"
    path.write_text(content + tiers + LINGUISTIC_TYPES + "</ANNOTATION_DOCUMENT>")
    return str(path)


def test_an_alignable_tier_is_read_in_seconds(tmp_path: Path):
    tier = (
        '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="default">'
        + alignable("a1", "ts1", "ts2", "hello")
        + alignable("a2", "ts2", "ts3", "world")
        + "</TIER>"
    )

    [result] = read_tiers(write_eaf(tmp_path, tier))

    assert result == {
        "name": "default",
        "labels": [(0.5, 1.5, "hello"), (1.5, 3.0, "world")],
    }


def test_empty_annotations_are_left_out(tmp_path: Path):
    tier = (
        '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="t">'
        + alignable("a1", "ts1", "ts2", "")
        + alignable("a2", "ts2", "ts3", "kept")
        + "</TIER>"
    )

    [result] = read_tiers(write_eaf(tmp_path, tier))

    assert result["labels"] == [(1.5, 3.0, "kept")]


def test_a_time_slot_without_a_time_falls_between_its_neighbours(tmp_path: Path):
    tier = (
        '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="t">'
        + alignable("a1", "ts1", "ts2", "x")
        + alignable("a2", "ts2", "ts3", "y")
        + "</TIER>"
    )

    [result] = read_tiers(
        write_eaf(tmp_path, tier, {"ts1": 1000, "ts2": None, "ts3": 3000})
    )

    assert result["labels"] == [(1.0, 2.0, "x"), (2.0, 3.0, "y")]


def test_an_association_takes_the_times_of_its_parent(tmp_path: Path):
    tiers = (
        '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="words">'
        + alignable("a1", "ts1", "ts2", "hello")
        + "</TIER>"
        + '<TIER LINGUISTIC_TYPE_REF="assoc" PARENT_REF="words" TIER_ID="gloss">'
        + reference("a2", "a1", "greeting")
        + "</TIER>"
    )

    _words, gloss = read_tiers(write_eaf(tmp_path, tiers))

    assert gloss == {"name": "gloss", "labels": [(0.5, 1.5, "greeting")]}


def test_a_tier_may_come_before_the_tier_it_refers_to(tmp_path: Path):
    tiers = (
        '<TIER LINGUISTIC_TYPE_REF="assoc" PARENT_REF="words" TIER_ID="gloss">'
        + reference("a2", "a1", "greeting")
        + "</TIER>"
        + '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="words">'
        + alignable("a1", "ts1", "ts2", "hello")
        + "</TIER>"
    )

    gloss, _words = read_tiers(write_eaf(tmp_path, tiers))

    assert gloss["labels"] == [(0.5, 1.5, "greeting")]


def test_subdivisions_share_the_interval_of_their_parent_equally(tmp_path: Path):
    tiers = (
        '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="words">'
        + alignable("a1", "ts1", "ts3", "ice cream")
        + "</TIER>"
        + '<TIER LINGUISTIC_TYPE_REF="subdiv" PARENT_REF="words" TIER_ID="parts">'
        + reference("a2", "a1", "ice")
        + reference("a3", "a1", "cream")
        + "</TIER>"
    )

    _words, parts = read_tiers(write_eaf(tmp_path, tiers))

    assert parts["labels"] == [(0.5, 1.75, "ice"), (1.75, 3.0, "cream")]


def test_a_file_that_is_not_xml_is_an_error(tmp_path: Path):
    path = tmp_path / "a.eaf"
    path.write_text("not xml at all")

    with pytest.raises(ValueError, match="ELAN"):
        read_tiers(str(path))


def test_subdivisions_follow_the_chain_ELAN_gives_them_not_the_file_order(
    tmp_path: Path,
):
    tiers = (
        '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="words">'
        + alignable("a1", "ts1", "ts3", "ice cream")
        + "</TIER>"
        + '<TIER LINGUISTIC_TYPE_REF="subdiv" PARENT_REF="words" TIER_ID="parts">'
        + reference("a3", "a1", "cream", previous="a2")
        + reference("a2", "a1", "ice")
        + "</TIER>"
    )

    _words, parts = read_tiers(write_eaf(tmp_path, tiers))

    assert parts["labels"] == [(0.5, 1.75, "ice"), (1.75, 3.0, "cream")]


def test_a_tier_can_refer_to_a_tier_that_itself_refers_to_another(tmp_path: Path):
    tiers = (
        '<TIER LINGUISTIC_TYPE_REF="subdiv" PARENT_REF="parts" TIER_ID="sounds">'
        + reference("a4", "a2", "i")
        + reference("a5", "a2", "s", previous="a4")
        + "</TIER>"
        + '<TIER LINGUISTIC_TYPE_REF="subdiv" PARENT_REF="words" TIER_ID="parts">'
        + reference("a2", "a1", "ice")
        + reference("a3", "a1", "cream", previous="a2")
        + "</TIER>"
        + '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="words">'
        + alignable("a1", "ts1", "ts3", "ice cream")
        + "</TIER>"
    )

    sounds, _parts, _words = read_tiers(write_eaf(tmp_path, tiers))

    assert sounds["labels"] == [(0.5, 1.125, "i"), (1.125, 1.75, "s")]


def test_times_are_milliseconds_whatever_the_header_says(tmp_path: Path):
    tier = (
        '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="t">'
        + alignable("a1", "ts1", "ts2", "x")
        + "</TIER>"
    )
    path = Path(write_eaf(tmp_path, tier, {"ts1": 1000, "ts2": 2000}))
    path.write_text(
        path.read_text().replace('TIME_UNITS="milliseconds"', 'TIME_UNITS="PAL-frames"')
    )

    [result] = read_tiers(str(path))

    assert result["labels"] == [(1.0, 2.0, "x")]


def test_an_annotation_whose_time_cannot_be_worked_out_is_an_error(tmp_path: Path):
    tier = (
        '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="t">'
        + alignable("a1", "ts1", "ts2", "x")
        + "</TIER>"
    )

    with pytest.raises(ValueError, match="a1"):
        read_tiers(write_eaf(tmp_path, tier, {"ts1": 1000, "ts2": None}))


def test_a_tier_that_names_a_participant_has_that_talker(tmp_path: Path):
    tiers = (
        '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="a-words" PARTICIPANT=" ann ">'
        + alignable("a1", "ts1", "ts2", "hello")
        + "</TIER>"
        + '<TIER LINGUISTIC_TYPE_REF="default-lt" TIER_ID="notes">'
        + alignable("a2", "ts2", "ts3", "x")
        + "</TIER>"
    )

    words, notes = read_tiers(write_eaf(tmp_path, tiers))

    assert words["talker"] == "ann"
    assert "talker" not in notes
