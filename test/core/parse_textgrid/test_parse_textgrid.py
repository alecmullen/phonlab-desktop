from pathlib import Path

import pytest

from core.annotation.entity.annotation import Annotation, AnnotationLabel
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.parse_textgrid.parse_textgrid import ParseTextGrid, ParseTextGridError
from phonlab_project.constants import SAME_NODE_THRESHOLD
from phonlab_project.readers.table_format import TierFile

SIMPLE_TEXTGRID = """File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1.0
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "word"
        xmin = 0
        xmax = 1.0
        intervals: size = 2
        intervals [1]:
            xmin = 0
            xmax = 0.5
            text = "hello"
        intervals [2]:
            xmin = 0.5
            xmax = 1.0
            text = "world"
"""

TWO_TIER_TEXTGRID = """File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1.0
tiers? <exists>
size = 2
item []:
    item [1]:
        class = "IntervalTier"
        name = "word"
        xmin = 0
        xmax = 1.0
        intervals: size = 1
        intervals [1]:
            xmin = 0
            xmax = 1.0
            text = "hi"
    item [2]:
        class = "IntervalTier"
        name = "phone"
        xmin = 0
        xmax = 1.0
        intervals: size = 2
        intervals [1]:
            xmin = 0
            xmax = 0.4
            text = "h"
        intervals [2]:
            xmin = 0.4
            xmax = 1.0
            text = "ay"
"""

POINT_TIER_TEXTGRID = """File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1.0
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "TextTier"
        name = "mark"
        xmin = 0
        xmax = 1.0
        points: size = 2
        points [1]:
            number = 0.25
            mark = "a"
        points [2]:
            number = 0.75
            mark = "b"
"""

UNKNOWN_TIER_TEXTGRID = """File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1.0
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "UnknownTier"
        name = "word"
        xmin = 0
        xmax = 1.0
"""


def write_textgrid(
    tmp_path: Path, content: str, name: str = "sample.TextGrid", encoding: str = "utf-8"
) -> str:
    path = tmp_path / name
    path.write_text(content, encoding=encoding)
    return str(path)


def parse(path: Path) -> Annotation:
    """ParseTextGrid is a generator; the annotation is its single yielded value"""
    return next(ParseTextGrid(InMemAnnotationRepository())(str(path), "sample"))


def label_times(annotation: Annotation, tier: int) -> list[tuple]:
    nodes = annotation.nodes
    return [
        (nodes[label.s_node], nodes[label.e_node], label.label)
        for label in annotation.types[tier].labels
    ]


# --------------------------- invoke ---------------------------


def test_invoke_parses_single_tier_textgrid(tmp_path: Path):
    path = write_textgrid(tmp_path, SIMPLE_TEXTGRID)

    result = parse(path)

    assert result.nodes == {0: 0.0, 1: 0.5, 2: 1.0}
    assert len(result.types) == 1
    assert result.types[0].type == "word"
    assert result.types[0].labels == [
        AnnotationLabel(0, 1, "hello", id=0),
        AnnotationLabel(1, 2, "world", id=1),
    ]


def test_invoke_parses_multiple_tiers_sharing_nodes(tmp_path: Path):
    path = write_textgrid(tmp_path, TWO_TIER_TEXTGRID)

    result = parse(path)

    assert sorted(result.nodes.values()) == [0.0, 0.4, 1.0]
    assert [t.type for t in result.types] == ["word", "phone"]
    assert label_times(result, 0) == [(0.0, 1.0, "hi")]
    assert label_times(result, 1) == [(0.0, 0.4, "h"), (0.4, 1.0, "ay")]


def test_invoke_merges_boundaries_within_threshold_across_tiers(tmp_path: Path):
    nudged = 0.4 + SAME_NODE_THRESHOLD / 2
    content = TWO_TIER_TEXTGRID.replace(
        'xmin = 0.4\n            xmax = 1.0\n            text = "ay"',
        f'xmin = {nudged}\n            xmax = 1.0\n            text = "ay"',
    )
    path = write_textgrid(tmp_path, content)

    result = parse(path)

    # the "h"/"ay" boundary (0.4 vs 0.4 + threshold/2) should collapse to one node
    assert sorted(result.nodes.values()) == [0.0, 0.4, 1.0]


def test_invoke_parses_point_tier(tmp_path: Path):
    path = write_textgrid(tmp_path, POINT_TIER_TEXTGRID)

    result = parse(path)

    assert result.nodes == {0: 0.25, 1: 0.75}
    assert len(result.types) == 1
    assert result.types[0].type == "mark"
    # a point's start and end node are the same, since it has zero duration
    assert result.types[0].labels == [
        AnnotationLabel(0, 0, "a", id=0),
        AnnotationLabel(1, 1, "b", id=1),
    ]


def test_invoke_raises_parse_text_grid_error_for_unknown_tier_type(tmp_path: Path):
    path = write_textgrid(tmp_path, UNKNOWN_TIER_TEXTGRID)

    with pytest.raises(ParseTextGridError):
        parse(path)


def test_invoke_raises_parse_text_grid_error_for_truncated_file(tmp_path: Path):
    path = write_textgrid(tmp_path, "xmin = 0\nxmax = 1.0\n")

    with pytest.raises(ParseTextGridError):
        parse(path)


def test_invoke_reads_utf_16_file(tmp_path: Path):
    path = write_textgrid(tmp_path, TWO_TIER_TEXTGRID, encoding="utf-16")

    result = parse(path)

    assert sorted(result.nodes.values()) == [0.0, 0.4, 1.0]
    assert [t.type for t in result.types] == ["word", "phone"]
    assert label_times(result, 0) == [(0.0, 1.0, "hi")]
    assert label_times(result, 1) == [(0.0, 0.4, "h"), (0.4, 1.0, "ay")]


def test_invoke_fills_annotation_already_registered_for_the_stem(tmp_path: Path):
    path = write_textgrid(tmp_path, SIMPLE_TEXTGRID)
    repository = InMemAnnotationRepository()
    repository.create_annotations_if_missing(["sample"])
    registered = repository.find_annotation_by_file_stem("sample")

    result = next(ParseTextGrid(repository)(path, "sample"))

    assert result.id == registered.id
    assert result.types[0].type == "word"
    assert len(repository.filenames) == 1


def test_invoke_raises_when_stem_already_has_annotation_content(tmp_path: Path):
    path = write_textgrid(tmp_path, SIMPLE_TEXTGRID)
    repository = InMemAnnotationRepository()
    parse_use_case = ParseTextGrid(repository)
    next(parse_use_case(path, "sample"))

    with pytest.raises(ParseTextGridError):
        next(parse_use_case(path, "sample"))


def test_invoke_replaces_existing_annotation_when_overwrite_is_true(tmp_path: Path):
    repository = InMemAnnotationRepository()
    parse_use_case = ParseTextGrid(repository)
    next(parse_use_case(write_textgrid(tmp_path, TWO_TIER_TEXTGRID), "sample"))
    path = write_textgrid(tmp_path, SIMPLE_TEXTGRID, "other.TextGrid")

    result = next(parse_use_case(path, "sample", overwrite=True))

    assert [type.type for type in result.types] == ["word"]
    assert len(repository.filenames) == 1
    assert repository.get_annotation_by_id(result.get_id()) == result


def test_invoke_keeps_existing_annotation_when_overwriting_with_an_unreadable_file(
    tmp_path: Path,
):
    repository = InMemAnnotationRepository()
    parse_use_case = ParseTextGrid(repository)
    original = next(
        parse_use_case(write_textgrid(tmp_path, TWO_TIER_TEXTGRID), "sample")
    )
    broken = write_textgrid(tmp_path, "xmin = 0\nxmax = 1.0\n", "broken.TextGrid")

    with pytest.raises(ParseTextGridError):
        next(parse_use_case(broken, "sample", overwrite=True))

    assert repository.find_annotation_by_file_stem("sample") == original


def test_invoke_overwrite_leaves_the_annotations_of_other_files_alone(tmp_path: Path):
    repository = InMemAnnotationRepository()
    parse_use_case = ParseTextGrid(repository)
    next(parse_use_case(write_textgrid(tmp_path, TWO_TIER_TEXTGRID), "one"))
    other = next(parse_use_case(write_textgrid(tmp_path, TWO_TIER_TEXTGRID), "two"))
    path = write_textgrid(tmp_path, SIMPLE_TEXTGRID, "replacement.TextGrid")

    next(parse_use_case(path, "one", overwrite=True))

    assert repository.find_annotation_by_file_stem("two") == other
    one = repository.find_annotation_by_file_stem("one")
    assert one is not None and [type.type for type in one.types] == ["word"]


def test_invoke_reads_a_buckeye_file(tmp_path: Path):
    (tmp_path / "s.words").write_text("h\n#\n  0.5000 121 hi; h ay; h ay; UH\n")
    (tmp_path / "s.phones").write_text("h\n#\n  0.2000 122 h\n  0.5000 122 ay\n")

    result = ParseTextGrid(InMemAnnotationRepository()).run_sync(
        str(tmp_path / "s.words"), "s"
    )

    assert [type.type for type in result.types] == ["word", "phone"]


# --------------------------- tiers in files of their own ---------------------------


def test_tiers_can_come_from_text_tables_without_a_textgrid(tmp_path: Path):
    phones = tmp_path / "a_phn.txt"
    phones.write_text("0 400 h\n400 1000 ay\n")
    words = tmp_path / "a_wrd.txt"
    words.write_text("0 1000 hi\n")

    result = next(
        ParseTextGrid(InMemAnnotationRepository())(
            None,
            "a",
            tier_files={"Phone": TierFile(str(phones)), "Word": TierFile(str(words))},
        )
    )

    assert [t.type for t in result.types] == ["Phone", "Word"]
    assert label_times(result, 0) == [(0.0, 400.0, "h"), (400.0, 1000.0, "ay")]


def test_tiers_from_text_tables_are_added_to_those_of_a_textgrid(tmp_path: Path):
    grid = write_textgrid(tmp_path, SIMPLE_TEXTGRID)
    sentence = tmp_path / "a_snt.txt"
    sentence.write_text("0 1 hello world\n")

    result = next(
        ParseTextGrid(InMemAnnotationRepository())(
            grid, "a", tier_files={"Sentence": TierFile(str(sentence))}
        )
    )

    assert [t.type for t in result.types] == ["word", "Sentence"]


def test_an_unreadable_tier_table_leaves_the_database_alone(tmp_path: Path):
    bad = tmp_path / "a_phn.txt"
    bad.write_text("0 1 x\nnot an interval\n")
    repository = InMemAnnotationRepository()

    with pytest.raises(ParseTextGridError):
        next(
            ParseTextGrid(repository)(
                None, "a", tier_files={"Phone": TierFile(str(bad))}
            )
        )

    assert repository.find_annotation_by_file_stem("a") is None


def test_labels_take_the_node_nearest_their_time_when_tiers_nearly_agree(
    tmp_path: Path,
):
    # the sentence begins and ends a hair after the phones do, which is the same node
    phones = tmp_path / "a_phn.txt"
    phones.write_text(
        "0 59.491978 sil\n59.491978 2647.727295 x\n2647.727295 2733.9 sil\n"
    )
    sentence = tmp_path / "a_snt.txt"
    sentence.write_text("59.492 2647.7273 hello there\n")

    result = next(
        ParseTextGrid(InMemAnnotationRepository())(
            None,
            "a",
            tier_files={
                "Phone": TierFile(str(phones)),
                "Sentence": TierFile(str(sentence)),
            },
        )
    )

    [label] = result.types[1].labels
    assert result.nodes[label.s_node] == pytest.approx(59.491978, abs=1e-3)
    assert result.nodes[label.e_node] == pytest.approx(2647.727295, abs=1e-3)


def test_a_tier_that_says_who_produced_it_keeps_its_talker(tmp_path: Path):
    eaf = tmp_path / "a.eaf"
    eaf.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<ANNOTATION_DOCUMENT FORMAT="3.0" VERSION="3.0">
<HEADER TIME_UNITS="milliseconds"/>
<TIME_ORDER><TIME_SLOT TIME_SLOT_ID="t1" TIME_VALUE="0"/>
<TIME_SLOT TIME_SLOT_ID="t2" TIME_VALUE="1000"/></TIME_ORDER>
<TIER LINGUISTIC_TYPE_REF="lt" TIER_ID="a-words" PARTICIPANT="ann"><ANNOTATION>
<ALIGNABLE_ANNOTATION ANNOTATION_ID="a1" TIME_SLOT_REF1="t1" TIME_SLOT_REF2="t2">
<ANNOTATION_VALUE>hello</ANNOTATION_VALUE></ALIGNABLE_ANNOTATION></ANNOTATION></TIER>
<TIER LINGUISTIC_TYPE_REF="lt" TIER_ID="notes"/>
<LINGUISTIC_TYPE LINGUISTIC_TYPE_ID="lt" TIME_ALIGNABLE="true"/>
</ANNOTATION_DOCUMENT>
"""
    )

    result = next(ParseTextGrid(InMemAnnotationRepository())(str(eaf), "a"))

    assert [(t.type, t.talker) for t in result.types] == [
        ("a-words", "ann"),
        ("notes", None),
    ]


def test_each_talker_of_a_subtitle_file_gets_a_tier(tmp_path: Path):
    srt_file = tmp_path / "a.srt"
    srt_file.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nAnn: Hi\n\n"
        "2\n00:00:02,000 --> 00:00:03,000\nBob: Hello\n"
    )

    result = next(ParseTextGrid(InMemAnnotationRepository())(str(srt_file), "a"))

    assert [(t.type, t.talker) for t in result.types] == [
        ("Ann", "Ann"),
        ("Bob", "Bob"),
    ]
    assert [label.label for label in result.types[1].labels] == ["Hello"]
