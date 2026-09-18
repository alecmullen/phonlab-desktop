import re
from pathlib import Path

import pytest

from core.parse_textgrid.annotation import AnnotationLabel
from core.parse_textgrid.parse_textgrid import (
    SAME_NODE_THRESHOLD,
    ParseTextGrid,
    ParseTextGridError,
    get_next_match,
    get_or_add_node,
)

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


def make_use_case(
    tmp_path: Path, content: str, name: str = "sample.TextGrid"
) -> ParseTextGrid:
    path = tmp_path / name
    path.write_text(content)
    return ParseTextGrid(str(path))


# --------------------------- invoke ---------------------------


def test_invoke_parses_single_tier_textgrid(tmp_path: Path):
    use_case = make_use_case(tmp_path, SIMPLE_TEXTGRID)

    result = use_case.invoke()

    assert result.nodes == {0: 0.0, 1: 0.5, 2: 1.0}
    assert len(result.types) == 1
    assert result.types[0].type == "word"
    assert result.types[0].labels == [
        AnnotationLabel(0, 1, "hello"),
        AnnotationLabel(1, 2, "world"),
    ]


def test_invoke_parses_multiple_tiers_sharing_nodes(tmp_path: Path):
    use_case = make_use_case(tmp_path, TWO_TIER_TEXTGRID)

    result = use_case.invoke()

    assert result.nodes == {0: 0.0, 1: 0.4, 2: 1.0}
    assert [t.type for t in result.types] == ["word", "phone"]
    assert result.types[0].labels == [AnnotationLabel(0, 2, "hi")]
    assert result.types[1].labels == [
        AnnotationLabel(0, 1, "h"),
        AnnotationLabel(1, 2, "ay"),
    ]


def test_invoke_merges_boundaries_within_threshold_across_tiers(tmp_path: Path):
    nudged = 0.4 + SAME_NODE_THRESHOLD / 2
    content = TWO_TIER_TEXTGRID.replace(
        'xmin = 0.4\n            xmax = 1.0\n            text = "ay"',
        f'xmin = {nudged}\n            xmax = 1.0\n            text = "ay"',
    )
    use_case = make_use_case(tmp_path, content)

    result = use_case.invoke()

    # the "h"/"ay" boundary (0.4 vs 0.4 + threshold/2) should collapse to one node
    assert result.nodes == {0: 0.0, 1: 0.4, 2: 1.0}


def test_invoke_parses_point_tier(tmp_path: Path):
    use_case = make_use_case(tmp_path, POINT_TIER_TEXTGRID)

    result = use_case.invoke()

    assert result.nodes == {0: 0.25, 1: 0.75}
    assert len(result.types) == 1
    assert result.types[0].type == "mark"
    # a point's start and end node are the same, since it has zero duration
    assert result.types[0].labels == [
        AnnotationLabel(0, 0, "a"),
        AnnotationLabel(1, 1, "b"),
    ]


def test_invoke_raises_parse_text_grid_error_for_unknown_tier_type(tmp_path: Path):
    use_case = make_use_case(tmp_path, UNKNOWN_TIER_TEXTGRID)

    with pytest.raises(ParseTextGridError):
        use_case.invoke()


def test_invoke_raises_syntax_error_for_truncated_file(tmp_path: Path):
    use_case = make_use_case(tmp_path, "xmin = 0\nxmax = 1.0\n")

    with pytest.raises(SyntaxError):
        use_case.invoke()


# --------------------------- get_next_float / get_next_int / get_next_quoted_string ---------------------------


def test_get_next_float_parses_decimal_and_skips_preceding_tokens():
    use_case = ParseTextGrid("unused.TextGrid")
    words = iter(["xmin", "=", "-1.25", "next"])

    assert use_case.get_next_float(words) == -1.25


def test_get_next_int_parses_integer_and_skips_preceding_tokens():
    use_case = ParseTextGrid("unused.TextGrid")
    words = iter(["size", "=", "3"])

    assert use_case.get_next_int(words) == 3


def test_get_next_quoted_string_strips_quotes():
    use_case = ParseTextGrid("unused.TextGrid")
    words = iter(["name", "=", '"hello world"'])

    assert use_case.get_next_quoted_string(words) == "hello world"


def test_get_next_float_raises_when_no_match_found():
    use_case = ParseTextGrid("unused.TextGrid")
    words = iter(["no", "numbers", "here"])

    with pytest.raises(SyntaxError):
        use_case.get_next_float(words)


# --------------------------- get_next_match ---------------------------


def test_get_next_match_returns_first_matching_token():
    words = iter(["Object", "0", "1.5"])

    match = get_next_match(words, re.compile(r"[-+]?\d+"))

    assert match.group() == "0"


def test_get_next_match_skips_non_matching_tokens():
    words = iter(["File", "type", "=", "42"])

    match = get_next_match(words, re.compile(r"[-+]?\d+"))

    assert match.group() == "42"


def test_get_next_match_raises_syntax_error_when_exhausted():
    words = iter(["File", "type"])

    with pytest.raises(SyntaxError):
        get_next_match(words, re.compile(r"[-+]?\d+"))


# --------------------------- get_or_add_node ---------------------------


def test_get_or_add_node_inserts_new_time_in_sorted_position():
    result = get_or_add_node([0.0, 1.0], 0.5)

    assert result == [0.0, 0.5, 1.0]


def test_get_or_add_node_merges_when_within_threshold_of_next_node():
    result = get_or_add_node([0.0, 0.5, 1.0], 0.5 + SAME_NODE_THRESHOLD / 2)

    assert result == [0.0, 0.5, 1.0]


def test_get_or_add_node_merges_when_within_threshold_of_previous_node():
    result = get_or_add_node([0.0, 0.5, 1.0], 0.5 - SAME_NODE_THRESHOLD / 2)

    assert result == [0.0, 0.5, 1.0]


def test_get_or_add_node_keeps_separate_nodes_when_beyond_threshold():
    new_time = 0.5 + SAME_NODE_THRESHOLD * 2

    result = get_or_add_node([0.0, 0.5, 1.0], new_time)

    assert result == [0.0, 0.5, new_time, 1.0]


def test_get_or_add_node_handles_empty_list():
    result = get_or_add_node([], 0.25)

    assert result == [0.25]
