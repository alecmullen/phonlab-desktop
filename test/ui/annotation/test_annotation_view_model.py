from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import pytest
from pytestqt.qtbot import QtBot

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
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
    assert "Error parsing TextGrid" in status_messages[0].message
    assert view_model.annotation_state.nodes == {}
    assert view_model.annotation_state.types == []


def test_select_label_emits_selected_state_from_node_positions(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=2.0)

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.select_label(AnnotationLabelState(s_node=0, e_node=2, label="x"))

    assert blocker.args[0] == AnnotationSelectedState(0.0, 2.0)


def test_select_label_with_missing_node_raises(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=2.0)

    with pytest.raises(ValueError):
        view_model.select_label(AnnotationLabelState(s_node=0, e_node=99, label="x"))


def make_annotation_view_model(
    nodes: dict[int, float],
    tiers: list[list[tuple[int, int, str]]],
    start: float = 0.0,
    end: float = 3.0,
) -> AnnotationViewModel:
    view_model = AnnotationViewModel()
    view_model.window_state = (start, end)
    view_model.set_annotation_state(
        Annotation(
            nodes=nodes,
            types=[
                AnnotationType(
                    f"tier{idx}",
                    [AnnotationLabel(id, *label) for id, label in enumerate(labels)],
                )
                for idx, labels in enumerate(tiers)
            ],
        )
    )
    return view_model


def label_spans(view_model: AnnotationViewModel, tier: int) -> list[tuple]:
    return sorted(
        (label.s_node, label.e_node, label.label)
        for label in view_model.annotation_state.types[tier].labels
    )


def test_delete_node_missing_node_raises(qtbot: QtBot):
    view_model = make_annotation_view_model({0: 0.0, 1: 1.0}, [[(0, 1, "a")]], end=1.0)

    with pytest.raises(ValueError):
        view_model.delete_node(99)


def test_delete_node_merges_adjacent_interval_labels(qtbot: QtBot):
    view_model = make_annotation_view_model(
        {0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]]
    )
    first_label_id = view_model.annotation_state.types[0].labels[0].id

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.delete_node(1)

    labels = view_model.annotation_state.types[0].labels
    assert len(labels) == 1
    assert labels[0].id == first_label_id
    assert (labels[0].s_node, labels[0].e_node, labels[0].label) == (0, 2, "ab")
    assert 1 not in view_model.annotation_view_state.nodes
    assert blocker.args[0] is view_model.annotation_view_state


def test_delete_node_merges_labels_on_every_tier_at_node(qtbot: QtBot):
    view_model = make_annotation_view_model(
        {0: 0.0, 1: 1.0, 2: 2.0},
        [[(0, 1, "a"), (1, 2, "b")], [(0, 1, "c"), (1, 2, "d")]],
    )

    view_model.delete_node(1)

    assert label_spans(view_model, 0) == [(0, 2, "ab")]
    assert label_spans(view_model, 1) == [(0, 2, "cd")]


def test_delete_node_leaves_other_tiers_untouched(qtbot: QtBot):
    view_model = make_annotation_view_model(
        {0: 0.0, 1: 1.0, 2: 2.0, 3: 1.5},
        [[(0, 1, "a"), (1, 2, "b")], [(0, 3, "c"), (3, 2, "d")]],
    )

    view_model.delete_node(1)

    assert label_spans(view_model, 0) == [(0, 2, "ab")]
    assert label_spans(view_model, 1) == [(0, 3, "c"), (3, 2, "d")]


def test_delete_node_removes_point_label(qtbot: QtBot):
    view_model = make_annotation_view_model(
        {0: 0.5, 1: 1.5}, [[(0, 0, "x"), (1, 1, "y")]]
    )

    with qtbot.waitSignal(view_model.state_changed, timeout=1000):
        view_model.delete_node(0)

    assert label_spans(view_model, 0) == [(1, 1, "y")]
    assert 0 not in view_model.annotation_view_state.nodes


def test_delete_node_extends_label_to_next_node_on_same_tier(qtbot: QtBot):
    view_model = make_annotation_view_model(
        {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0},
        [[(0, 1, "a"), (3, 4, "b")], [(0, 2, "c"), (2, 4, "d")]],
        end=4.0,
    )

    view_model.delete_node(1)

    assert label_spans(view_model, 0) == [(0, 3, "a"), (3, 4, "b")]
    assert label_spans(view_model, 1) == [(0, 2, "c"), (2, 4, "d")]


def test_delete_node_with_ids_out_of_time_order(qtbot: QtBot):
    view_model = make_annotation_view_model(
        {5: 0.0, 3: 1.0, 0: 2.0, 1: 3.0},
        [[(5, 3, "a"), (0, 1, "b")]],
    )

    view_model.delete_node(3)

    assert label_spans(view_model, 0) == [(0, 1, "b"), (5, 0, "a")]


def test_delete_node_removes_node_from_state(qtbot: QtBot):
    view_model = make_annotation_view_model(
        {0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]]
    )

    view_model.delete_node(1)

    assert list(view_model.annotation_state.nodes) == [0, 2]


def test_delete_node_does_not_mutate_previous_state(qtbot: QtBot):
    view_model = make_annotation_view_model(
        {0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]]
    )
    previous = view_model.annotation_state
    previous_labels = list(previous.types[0].labels)

    view_model.delete_node(1)

    assert previous.types[0].labels == previous_labels
    assert 1 in previous.nodes


def test_delete_last_node_of_tier_with_attached_label_shows_status_message(
    qtbot: QtBot,
):
    view_model = make_annotation_view_model(
        {0: 0.0, 1: 1.0, 2: 2.0},
        [[(0, 1, "a")], [(0, 2, "b")]],
    )
    received = []
    view_model.subscribe(received.append)

    view_model.delete_node(1)

    assert received == [
        StatusMessageState("Cannot delete end node with attached label")
    ]
    assert label_spans(view_model, 0) == [(0, 1, "a")]
    assert 1 in view_model.annotation_state.nodes


@pytest.mark.parametrize("node", [0, 2])
def test_delete_end_node_with_attached_label_shows_status_message(
    qtbot: QtBot, node: int
):
    view_model = make_annotation_view_model(
        {0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]]
    )
    received = []
    view_model.subscribe(received.append)

    view_model.delete_node(node)

    assert received == [
        StatusMessageState("Cannot delete end node with attached label")
    ]
    assert label_spans(view_model, 0) == [(0, 1, "a"), (1, 2, "b")]
