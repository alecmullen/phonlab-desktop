from dataclasses import replace

import pyqtgraph as pg
import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent, QShowEvent
from pytestqt.qtbot import QtBot

from core.parse_textgrid.annotation import Annotation, AnnotationLabel, AnnotationType
from ui.annotation.annotation_plot import AnnotationPlot
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.state.annotation_node_state import (
    AnnotationNodeExtentState,
    AnnotationNodeState,
)
from ui.annotation.state.annotation_state import (
    AnnotationLabelState,
    AnnotationState,
    AnnotationTypeState,
)
from ui.base.state import State

MOCK_ANNOTATION_STATE = AnnotationState(
    nodes={
        0: AnnotationNodeState(0, -1.0, is_visible=False),
        1: AnnotationNodeState(
            1, 0.0, extents=[AnnotationNodeExtentState(0)], is_visible=True
        ),
        2: AnnotationNodeState(
            2, 1.0, extents=[AnnotationNodeExtentState(0)], is_visible=True
        ),
        3: AnnotationNodeState(
            3, 4.0, extents=[AnnotationNodeExtentState(0)], is_visible=True
        ),
        4: AnnotationNodeState(4, 5.0, is_visible=False),
    },
    types=[
        AnnotationTypeState(
            "word",
            [
                AnnotationLabelState(
                    1, 2, "one", is_visible=True, pos=(1.5, 0.5), size=(1.0, 1.0)
                ),
                AnnotationLabelState(
                    2, 3, "two", is_visible=True, pos=(2.5, 0.5), size=(3.0, 1.0)
                ),
            ],
        )
    ],
)


def show_plot_in_layout(plot: AnnotationPlot) -> pg.GraphicsLayoutWidget:
    layout = pg.GraphicsLayoutWidget()
    layout.addItem(plot)
    layout.resize(400, 300)
    layout.show()
    return layout


def test_populate_adds_visible_nodes(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)

    plot.populate(MOCK_ANNOTATION_STATE)

    assert {node.node for node in plot.visible_nodes} == {1, 2, 3}


def test_populate_with_no_types_sets_empty_y_range_and_no_visible_nodes(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    state = replace(MOCK_ANNOTATION_STATE, nodes={0: 0.0}, types=[])

    plot.populate(state)

    assert plot.visible_nodes == []
    assert plot.getAxis("left").range == [-0.1, 0]


def test_populate_filters_invisible_labels(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)

    state = replace(
        MOCK_ANNOTATION_STATE,
        types=[
            AnnotationTypeState(
                "word",
                [
                    AnnotationLabelState(
                        0,
                        1,
                        "visible",
                        is_visible=True,
                        pos=(1.5, 0.5),
                        size=(1.0, 1.0),
                    ),
                    AnnotationLabelState(
                        2,
                        3,
                        "outside",
                        is_visible=False,
                        pos=(2.5, 0.5),
                        size=(3.0, 1.0),
                    ),
                ],
            )
        ],
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

    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)

    state_with_types = MOCK_ANNOTATION_STATE

    plot.populate(state_with_types)
    assert len(plot.getViewBox().addedItems) > 0

    empty_state = AnnotationState(nodes={}, types=[])
    plot.populate(empty_state)

    node_or_label_items = [
        item
        for item in plot.getViewBox().addedItems
        if hasattr(item, "labels") or hasattr(item, "nodes")
    ]
    assert node_or_label_items == []


def test_on_state_change_populates_for_annotation_state(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    calls = []
    monkeypatch.setattr(plot, "populate", lambda state: calls.append(state))

    plot.on_state_change(AnnotationState())

    assert calls == [AnnotationState()]


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

    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)

    state = Annotation(
        nodes={0: 0.0, 1: 1.0},
        types=[AnnotationType("word", [AnnotationLabel(0, 1, "hi")])],
    )

    view_model.set_annotation_state(state)
    view_model.set_window_state(0.0, 1.0)

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

    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)

    node_view_state = AnnotationNodeState(7, 0.0, [AnnotationNodeExtentState(0)])
    plot.visible_nodes = [node_view_state]
    scene_pos = plot.getViewBox().mapViewToScene(QPointF(0.0, 0.0))

    press_event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        scene_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    assert plot.handle_mouse_press(press_event) is True
    assert plot.dragging_node == node_view_state

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

    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)

    plot.visible_nodes = [AnnotationNodeState(7, 0.0, [AnnotationNodeExtentState(0)])]
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
    view_model.annotation_view_state = MOCK_ANNOTATION_STATE
    view_model.annotation_state = MOCK_ANNOTATION_STATE
    view_model.window_state = (0.0, 2.0)
    plot = AnnotationPlot(view_model)

    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)

    plot.dragging_node = AnnotationNodeState(
        1, view_model.annotation_state.nodes[1], []
    )
    scene_pos = plot.getViewBox().mapViewToScene(QPointF(1.5, 0.0))

    plot.on_mouse_moved(scene_pos)

    assert view_model.annotation_state.nodes[1].x == 1.5


def test_on_mouse_moved_without_dragging_moves_cursor_when_in_control(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)

    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
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


def test_show_time_axis_false_leaves_bottom_label_unset(qtbot: QtBot):
    plot = AnnotationPlot(AnnotationViewModel())

    plot.show_time_axis(False)

    assert plot.getAxis("bottom").labelText != "Time"


def test_handle_single_click_on_label_selects_it(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)
    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)

    label = MOCK_ANNOTATION_STATE.types[0].labels[0]
    plot.visible_labels = [label]
    selected = []
    monkeypatch_select = lambda lbl: selected.append(lbl)
    view_model.select_label = monkeypatch_select  # type: ignore[method-assign]

    scene_pos = plot.getViewBox().mapViewToScene(QPointF(1.5, 0.5))

    assert plot.handle_single_click(scene_pos) is True
    assert selected == [label]


def test_handle_single_click_outside_labels_returns_false(qtbot: QtBot):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)
    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)

    plot.visible_labels = [MOCK_ANNOTATION_STATE.types[0].labels[0]]
    scene_pos = plot.getViewBox().mapViewToScene(QPointF(50.0, 0.5))

    assert plot.handle_single_click(scene_pos) is False


def test_show_event_populates_from_view_model_state(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AnnotationViewModel()
    plot = AnnotationPlot(view_model)
    calls = []
    monkeypatch.setattr(plot, "populate", lambda state: calls.append(state))

    plot.showEvent(QShowEvent())

    assert calls == [view_model.annotation_view_state]
