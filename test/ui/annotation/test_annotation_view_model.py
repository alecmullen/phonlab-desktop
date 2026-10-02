from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import pytest
from pytestqt.qtbot import QtBot

from core.parse_textgrid.annotation import Annotation
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.state.annotation_label_state import AnnotationLabelState
from ui.annotation.state.annotation_node_state import (
    AnnotationNodeExtentState,
    AnnotationNodeState,
)
from ui.annotation.state.annotation_selected_state import AnnotationSelectedState
from ui.annotation.state.annotation_state import AnnotationState
from ui.document.state.status_message_state import StatusMessageState

MOCK_ANNOTATION_NODES = MappingProxyType(
    {
        0: AnnotationNodeState(
            0, 0.0, extents=[AnnotationNodeExtentState(0)], is_visible=True
        ),
        1: AnnotationNodeState(
            1,
            1.0,
            extents=[AnnotationNodeExtentState(0, has_point_label=True)],
            is_visible=True,
        ),
        2: AnnotationNodeState(
            2, 2.0, extents=[AnnotationNodeExtentState(0)], is_visible=True
        ),
    }
)


def make_view_model(
    nodes: dict[int, AnnotationNodeState], start: float, end: float
) -> AnnotationViewModel:
    view_model = AnnotationViewModel()
    view_model.annotation_state = AnnotationState(nodes=nodes, types=[])
    view_model.window_state = (start, end)
    view_model.annotation_view_state = AnnotationState(nodes=nodes, types=[])
    return view_model


def test_change_node_state_moves_node_within_bounds(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=2.0)

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.change_node_state(
            AnnotationNodeState(1, 1.0, [AnnotationNodeExtentState(0)]), 1.5
        )

    assert [node.x for node in view_model.annotation_state.nodes.values()] == [
        0.0,
        1.5,
        2.0,
    ]
    assert blocker.args[0] is view_model.annotation_view_state


def test_change_point_node_state_can_cross_other_nodes(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=3.0)

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.change_node_state(
            AnnotationNodeState(
                1, 1.0, [AnnotationNodeExtentState(0, has_point_label=True)]
            ),
            2.5,
        )

    assert [node.x for node in view_model.annotation_state.nodes.values()] == [
        0.0,
        2.5,
        2.0,
    ]
    assert blocker.args[0] is view_model.annotation_view_state


def test_change_node_state_bounds_position_before_start(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=-0.25, end=2.0)

    received = []
    view_model.subscribe(received.append)

    view_model.change_node_state(MOCK_ANNOTATION_NODES[0], -0.5)

    expected = MOCK_ANNOTATION_NODES.copy()
    expected[0] = replace(expected[0], x=-0.25)

    assert view_model.annotation_state.nodes == expected
    assert received == [view_model.annotation_view_state]


def test_change_node_state_bounds_position_after_end(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=3.0)

    received = []
    view_model.subscribe(received.append)

    view_model.change_node_state(MOCK_ANNOTATION_NODES[2], 5.0)

    expected = MOCK_ANNOTATION_NODES.copy()
    expected[2] = replace(expected[2], x=3.0)

    assert view_model.annotation_state.nodes == expected
    assert received == [view_model.annotation_view_state]


def test_change_interval_node_state_does_not_cross_later_nodes(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=3.0)

    view_model.change_node_state(
        AnnotationNodeState(0, 0.0, [AnnotationNodeExtentState(0)]), 1.5
    )

    assert [node.x for node in view_model.annotation_state.nodes.values()] == [
        1.0,
        1.0,
        2.0,
    ]


def test_change_interval_node_state_does_not_cross_earlier_nodes(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=3.0)

    view_model.change_node_state(
        AnnotationNodeState(2, 2.0, [AnnotationNodeExtentState(0)]), 0.5
    )

    assert [node.x for node in view_model.annotation_state.nodes.values()] == [
        0.0,
        1.0,
        1.0,
    ]


def test_set_annotation_state_replaces_state_and_emits(qtbot: QtBot):
    view_model = make_view_model({0: 0.0}, start=0.0, end=1.0)
    nodes = {0: 0.0, 1: 1.0}
    annotation = Annotation(nodes=nodes, types=[])

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.set_annotation_state(annotation)

    new_state = AnnotationState(
        nodes={idx: AnnotationNodeState(idx, x) for idx, x in nodes.items()}
    )

    assert view_model.annotation_state == new_state
    assert blocker.args[0] == view_model.annotation_view_state


TEXTGRID_FIXTURE = """File type = "ooTextFile"
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


def test_parse_textgrid_loads_annotation_state(tmp_path: Path):
    view_model = make_view_model({}, 0.0, 1.0)
    textgrid = tmp_path / "sample.TextGrid"
    textgrid.write_text(TEXTGRID_FIXTURE)

    view_model.parse_textgrid(str(textgrid))

    assert {node.x for node in view_model.annotation_state.nodes.values()} == {
        0.0,
        0.5,
        1.0,
    }
    assert [t.type for t in view_model.annotation_state.types] == ["word"]
    assert [label.label for label in view_model.annotation_state.types[0].labels] == [
        "hello",
        "world",
    ]


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
        points: size = 1
        points [1]:
            number = 0.5
            mark = "click"
"""


def test_parse_textgrid_loads_point_tier(tmp_path: Path):
    view_model = make_view_model({}, 0.0, 1.0)
    textgrid = tmp_path / "point.TextGrid"
    textgrid.write_text(POINT_TIER_TEXTGRID)

    view_model.parse_textgrid(str(textgrid))

    assert {node.x for node in view_model.annotation_state.nodes.values()} == {0.5}
    assert [t.type for t in view_model.annotation_state.types] == ["mark"]
    assert [label.label for label in view_model.annotation_state.types[0].labels] == [
        "click"
    ]


BROKEN_TIER_TEXTGRID = """File type = "ooTextFile"
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


def test_parse_textgrid_shows_status_message_on_invalid_tier_type(tmp_path: Path):
    view_model = make_view_model({}, 0.0, 1.0)
    textgrid = tmp_path / "broken.TextGrid"
    textgrid.write_text(BROKEN_TIER_TEXTGRID)
    received = []
    view_model.subscribe(received.append)

    view_model.parse_textgrid(str(textgrid))

    status_messages = [s for s in received if isinstance(s, StatusMessageState)]
    assert len(status_messages) == 1
    assert "Invalid Textgrid" in status_messages[0].message
    assert view_model.annotation_state.nodes == {}
    assert view_model.annotation_state.types == []


def test_select_label_emits_selected_state_from_node_positions(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=2.0)

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.select_label(AnnotationLabelState(0, 2, "x"))

    assert blocker.args[0] == AnnotationSelectedState(0.0, 2.0)


def test_select_label_with_missing_node_raises(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=2.0)

    with pytest.raises(ValueError):
        view_model.select_label(AnnotationLabelState(0, 99, "x"))
