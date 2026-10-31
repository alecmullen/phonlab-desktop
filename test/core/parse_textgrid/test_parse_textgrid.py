from pathlib import Path

import pytest
from support.annotation_repository import FakeAnnotationRepository

from core.annotation.entity.annotation import AnnotationLabel
from core.parse_textgrid.parse_textgrid import ParseTextGrid, ParseTextGridError
from res.constants import SAME_NODE_THRESHOLD

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


# --------------------------- invoke ---------------------------


def test_invoke_parses_single_tier_textgrid(tmp_path: Path):
    path = write_textgrid(tmp_path, SIMPLE_TEXTGRID)

    result = ParseTextGrid(FakeAnnotationRepository())(path)

    assert result.nodes == {0: 0.0, 1: 0.5, 2: 1.0}
    assert len(result.types) == 1
    assert result.types[0].type == "word"
    assert result.types[0].labels == [
        AnnotationLabel(0, 1, "hello", id=0),
        AnnotationLabel(1, 2, "world", id=1),
    ]


def test_invoke_parses_multiple_tiers_sharing_nodes(tmp_path: Path):
    path = write_textgrid(tmp_path, TWO_TIER_TEXTGRID)

    result = ParseTextGrid(FakeAnnotationRepository())(path)

    assert result.nodes == {0: 0.0, 1: 0.4, 2: 1.0}
    assert [t.type for t in result.types] == ["word", "phone"]
    assert result.types[0].labels == [AnnotationLabel(0, 2, "hi", id=0)]
    assert result.types[1].labels == [
        AnnotationLabel(0, 1, "h", id=0),
        AnnotationLabel(1, 2, "ay", id=1),
    ]


def test_invoke_merges_boundaries_within_threshold_across_tiers(tmp_path: Path):
    nudged = 0.4 + SAME_NODE_THRESHOLD / 2
    content = TWO_TIER_TEXTGRID.replace(
        'xmin = 0.4\n            xmax = 1.0\n            text = "ay"',
        f'xmin = {nudged}\n            xmax = 1.0\n            text = "ay"',
    )
    path = write_textgrid(tmp_path, content)

    result = ParseTextGrid(FakeAnnotationRepository())(path)

    # the "h"/"ay" boundary (0.4 vs 0.4 + threshold/2) should collapse to one node
    assert result.nodes == {0: 0.0, 1: 0.4, 2: 1.0}


def test_invoke_parses_point_tier(tmp_path: Path):
    path = write_textgrid(tmp_path, POINT_TIER_TEXTGRID)

    result = ParseTextGrid(FakeAnnotationRepository())(path)

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
        ParseTextGrid(FakeAnnotationRepository())(path)


def test_invoke_raises_parse_text_grid_error_for_truncated_file(tmp_path: Path):
    path = write_textgrid(tmp_path, "xmin = 0\nxmax = 1.0\n")

    with pytest.raises(ParseTextGridError):
        ParseTextGrid(FakeAnnotationRepository())(path)


def test_invoke_reads_utf_16_file(tmp_path: Path):
    path = write_textgrid(tmp_path, TWO_TIER_TEXTGRID, encoding="utf-16")

    result = ParseTextGrid(FakeAnnotationRepository())(path)

    assert result.nodes == {0: 0.0, 1: 0.4, 2: 1.0}
    assert [t.type for t in result.types] == ["word", "phone"]
    assert result.types[0].labels == [AnnotationLabel(0, 2, "hi", id=0)]
    assert result.types[1].labels == [
        AnnotationLabel(0, 1, "h", id=0),
        AnnotationLabel(1, 2, "ay", id=1),
    ]
