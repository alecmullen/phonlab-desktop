from pytestqt.qtbot import QtBot

from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.annotation_window_state import AnnotationWindowState
from ui.document.state.annotation_state import AnnotationState


def make_view_model(
    nodes: dict[int, float], start: float, end: float
) -> AnnotationViewModel:
    view_model = AnnotationViewModel()
    view_model.annotation_window_state = AnnotationWindowState(
        annotation_state=AnnotationState(nodes=dict(nodes), types=[]),
        start=start,
        end=end,
    )
    return view_model


def test_change_node_state_moves_node_within_bounds(qtbot: QtBot):
    view_model = make_view_model({0: 0.0, 1: 1.0, 2: 2.0}, start=0.0, end=2.0)

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.change_node_state(1, 1.5)

    assert view_model.annotation_window_state.annotation_state.nodes == {
        0: 0.0,
        1: 1.5,
        2: 2.0,
    }
    assert blocker.args[0] is view_model.annotation_window_state


def test_change_node_state_ignores_position_before_start(qtbot: QtBot):
    view_model = make_view_model({0: 0.0, 1: 1.0, 2: 2.0}, start=0.0, end=2.0)

    received = []
    view_model.subscribe(received.append)

    view_model.change_node_state(1, -0.5)

    assert view_model.annotation_window_state.annotation_state.nodes == {
        0: 0.0,
        1: 1.0,
        2: 2.0,
    }
    assert received == []


def test_change_node_state_ignores_position_after_end(qtbot: QtBot):
    view_model = make_view_model({0: 0.0, 1: 1.0, 2: 2.0}, start=0.0, end=2.0)

    received = []
    view_model.subscribe(received.append)

    view_model.change_node_state(1, 5.0)

    assert view_model.annotation_window_state.annotation_state.nodes == {
        0: 0.0,
        1: 1.0,
        2: 2.0,
    }
    assert received == []


def test_change_node_state_pushes_later_nodes_forward(qtbot: QtBot):
    view_model = make_view_model({0: 0.0, 1: 1.0, 2: 2.0}, start=0.0, end=3.0)

    view_model.change_node_state(1, 2.5)

    assert view_model.annotation_window_state.annotation_state.nodes == {
        0: 0.0,
        1: 2.5,
        2: 2.5,
    }


def test_change_node_state_pushes_earlier_nodes_backward(qtbot: QtBot):
    view_model = make_view_model({0: 1.0, 1: 2.0, 2: 3.0}, start=0.0, end=3.0)

    view_model.change_node_state(1, 0.5)

    assert view_model.annotation_window_state.annotation_state.nodes == {
        0: 0.5,
        1: 0.5,
        2: 3.0,
    }


def test_set_annotation_state_replaces_state_and_emits(qtbot: QtBot):
    view_model = make_view_model({0: 0.0}, start=0.0, end=1.0)
    new_state = AnnotationWindowState(
        annotation_state=AnnotationState(nodes={0: 0.0, 1: 1.0}, types=[]),
        start=0.0,
        end=1.0,
    )

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.set_annotation_state(new_state)

    assert view_model.annotation_window_state is new_state
    assert blocker.args[0] is new_state
