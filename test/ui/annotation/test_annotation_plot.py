import pyqtgraph as pg
import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from pytestqt.qtbot import QtBot

from ui.annotation.annotation_plot import AnnotationPlot
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.annotation_window_state import AnnotationWindowState
from ui.annotation.state.node_view_state import NodeViewState
from ui.base.state import State
from ui.document.state.annotation_state import (
    AnnotationLabelState,
    AnnotationState,
    AnnotationTypeState,
)


def make_window_state(
    nodes: dict[int, float],
    types: list[AnnotationTypeState],
    start: float,
    end: float,
) -> AnnotationWindowState:
    return AnnotationWindowState(
        annotation_state=AnnotationState(nodes=nodes, types=types),
        start=start,
        end=end,
    )


def test_populate_computes_visible_nodes_within_start_and_end(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    state = make_window_state(
        nodes={0: -1.0, 1: 0.0, 2: 1.0, 3: 2.0, 4: 5.0},
        types=[
            AnnotationTypeState(
                "word",
                [
                    AnnotationLabelState(1, 2, "a"),
                    AnnotationLabelState(2, 3, "b"),
                ],
            )
        ],
        start=0.0,
        end=2.0,
    )

    plot.populate(state)

    assert set(plot.visible_nodes.keys()) == {1, 2, 3}
    assert plot.visible_nodes[1].x == 0.0
    assert plot.visible_nodes[3].x == 2.0


def test_populate_with_no_types_sets_empty_y_range_and_no_visible_nodes(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    state = make_window_state(nodes={0: 0.0}, types=[], start=0.0, end=1.0)

    plot.populate(state)

    assert plot.visible_nodes == {}
    assert plot.getAxis("left").range == [-0.1, 0]


def test_populate_filters_labels_outside_visible_range(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    state = make_window_state(
        nodes={0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0},
        types=[
            AnnotationTypeState(
                "word",
                [
                    AnnotationLabelState(0, 1, "visible"),
                    AnnotationLabelState(2, 3, "outside"),
                ],
            )
        ],
        start=0.0,
        end=1.0,
    )

    plot.populate(state)

    label_items = [
        item for item in plot.getViewBox().addedItems if hasattr(item, "labels")
    ]
    assert len(label_items) == 1
    rendered_labels = [label.label for label in label_items[0].labels]
    assert rendered_labels == ["visible"]


def test_populate_clears_previous_items(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    state_with_types = make_window_state(
        nodes={0: 0.0, 1: 1.0},
        types=[AnnotationTypeState("word", [AnnotationLabelState(0, 1, "hi")])],
        start=0.0,
        end=1.0,
    )
    plot.populate(state_with_types)
    assert len(plot.getViewBox().addedItems) > 0

    empty_state = make_window_state(nodes={}, types=[], start=0.0, end=1.0)
    plot.populate(empty_state)

    node_or_label_items = [
        item
        for item in plot.getViewBox().addedItems
        if hasattr(item, "labels") or hasattr(item, "nodes")
    ]
    assert node_or_label_items == []


def test_on_state_change_populates_for_annotation_window_state(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    calls = []
    monkeypatch.setattr(plot, "populate", lambda state: calls.append(state))

    state = make_window_state({}, [], 0.0, 1.0)
    plot.on_state_change(state)

    assert calls == [state]


def test_on_state_change_ignores_other_state_types(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    calls = []
    monkeypatch.setattr(plot, "populate", lambda state: calls.append(state))

    plot.on_state_change(State())

    assert calls == []


def test_view_model_state_change_triggers_populate(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    state = make_window_state(
        nodes={0: 0.0, 1: 1.0},
        types=[AnnotationTypeState("word", [AnnotationLabelState(0, 1, "hi")])],
        start=0.0,
        end=1.0,
    )

    view_model.set_annotation_state(state)

    assert plot.visible_nodes[0].x == 0.0
    assert plot.visible_nodes[1].x == 1.0


def test_show_time_axis_true_sets_bottom_label(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    plot.show_time_axis(True)

    assert plot.getAxis("bottom").labelText == "Time"


def test_handle_mouse_release_without_drag_returns_false(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    event = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    assert plot.handle_mouse_release(event) is False
    assert plot.dragging_node is None


def test_handle_mouse_press_and_release_on_node(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    layout = pg.GraphicsLayoutWidget()
    qtbot.addWidget(layout)
    layout.addItem(plot)
    layout.resize(400, 300)
    layout.show()
    qtbot.waitExposed(layout)

    plot.visible_nodes = {7: NodeViewState(0.0, [0])}
    scene_pos = plot.getViewBox().mapViewToScene(QPointF(0.0, 0.0))

    press_event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        scene_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    assert plot.handle_mouse_press(press_event) is True
    assert plot.dragging_node == 7

    release_event = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        scene_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    assert plot.handle_mouse_release(release_event) is True
    assert plot.dragging_node is None


def test_handle_mouse_press_away_from_node_returns_false(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    layout = pg.GraphicsLayoutWidget()
    qtbot.addWidget(layout)
    layout.addItem(plot)
    layout.resize(400, 300)
    layout.show()
    qtbot.waitExposed(layout)

    plot.visible_nodes = {7: NodeViewState(0.0, [0])}
    far_scene_pos = plot.getViewBox().mapViewToScene(QPointF(100.0, 100.0))

    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        far_scene_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    assert plot.handle_mouse_press(event) is False
    assert plot.dragging_node is None


def test_on_mouse_moved_while_dragging_updates_node_state(qtbot: QtBot):
    view_model = AnnotationViewModel()
    view_model.annotation_window_state = make_window_state(
        {0: 0.0, 1: 1.0}, [], start=0.0, end=2.0
    )
    plot = AnnotationPlot(view_model)

    layout = pg.GraphicsLayoutWidget()
    qtbot.addWidget(layout)
    layout.addItem(plot)
    layout.resize(400, 300)
    layout.show()
    qtbot.waitExposed(layout)

    plot.dragging_node = 1
    scene_pos = plot.getViewBox().mapViewToScene(QPointF(1.5, 0.0))

    plot.on_mouse_moved(scene_pos)

    assert view_model.annotation_window_state.annotation_state.nodes[1] == 1.5


def test_on_mouse_moved_without_dragging_moves_cursor_when_in_control(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    layout = pg.GraphicsLayoutWidget()
    qtbot.addWidget(layout)
    layout.addItem(plot)
    layout.resize(400, 300)
    layout.show()
    qtbot.waitExposed(layout)

    plot.has_cursor_control = True
    scene_pos = plot.getViewBox().mapViewToScene(QPointF(0.75, 0.0))

    plot.on_mouse_moved(scene_pos)

    assert plot.cursor_line.value() == pytest.approx(0.75)


def test_set_cursor_position_moves_line_and_removes_control(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    plot.set_cursor_position(3.0)

    assert plot.cursor_line.value() == 3.0
    assert plot.has_cursor_control is False


def test_set_mark_position_moves_line_and_sets_visibility(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    assert plot.mark_line.isVisible() is False

    plot.set_mark_position(2.5, True)
    assert plot.mark_line.value() == 2.5
    assert plot.mark_line.isVisible() is True

    plot.set_mark_position(2.5, False)
    assert plot.mark_line.isVisible() is False
