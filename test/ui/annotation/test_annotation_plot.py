from dataclasses import replace

import pyqtgraph as pg
import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QFocusEvent, QKeyEvent, QKeySequence, QMouseEvent, QShowEvent
from pytestqt.qtbot import QtBot

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from ui.annotation.annotation_plot import AnnotationPlot
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.component.node_view import NodeView
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
from ui.common.context_menu_hint import ContextMenuHintAction

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
                    1, 1, 2, "one", is_visible=True, pos=(1.5, 0.5), size=(1.0, 1.0)
                ),
                AnnotationLabelState(
                    2, 2, 3, "two", is_visible=True, pos=(2.5, 0.5), size=(3.0, 1.0)
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
                        1,
                        0,
                        1,
                        "visible",
                        is_visible=True,
                        pos=(1.5, 0.5),
                        size=(1.0, 1.0),
                    ),
                    AnnotationLabelState(
                        2,
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
        types=[AnnotationType("word", [AnnotationLabel(0, 0, 1, "hi")])],
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
    press_event.scenePos = lambda: scene_pos
    plot.mousePressEvent(press_event)
    assert plot.dragging_node == node_view_state

    release_event = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        scene_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    release_event.scenePos = lambda: scene_pos
    plot.mouseReleaseEvent(release_event)
    assert plot.dragging_node is None


def test_mouse_press_away_from_node_does_not_start_drag(qtbot: QtBot):
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
    event.scenePos = lambda: far_scene_pos
    plot.mousePressEvent(event)  # type: ignore[arg-type]
    assert plot.dragging_node is None
    assert not event.isAccepted()


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


def _node_views(plot: AnnotationPlot) -> list[NodeView]:
    return [item for item in plot.items if isinstance(item, NodeView)]


def _key_event(key: Qt.Key) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)


def test_plot_has_no_selected_node_initially(qtbot: QtBot):
    plot = AnnotationPlot(AnnotationViewModel())

    assert plot.selected_node is None


def test_plot_accepts_focus_on_click(qtbot: QtBot):
    plot = AnnotationPlot(AnnotationViewModel())

    assert plot.focusPolicy() == Qt.FocusPolicy.ClickFocus


def test_populate_passes_no_selection_to_node_view(qtbot: QtBot):
    plot = AnnotationPlot(AnnotationViewModel())
    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)

    plot.populate(MOCK_ANNOTATION_STATE)

    node_views = _node_views(plot)
    assert len(node_views) == 1
    assert node_views[0].selected_node is None


def test_populate_passes_selected_node_to_node_view(qtbot: QtBot):
    plot = AnnotationPlot(AnnotationViewModel())
    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)
    plot.selected_node = 2

    plot.populate(MOCK_ANNOTATION_STATE)

    assert _node_views(plot)[0].selected_node == 2


def test_mouse_release_after_drag_selects_node_and_clears_drag(qtbot: QtBot):
    view_model = AnnotationViewModel()
    view_model.annotation_view_state = MOCK_ANNOTATION_STATE
    plot = AnnotationPlot(view_model)
    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)
    plot.dragging_node = MOCK_ANNOTATION_STATE.nodes[2]

    event = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    plot.mouseReleaseEvent(event)  # type: ignore[arg-type]

    assert plot.dragging_node is None
    assert plot.selected_node == 2


def test_mouse_release_after_drag_rerenders_node_as_selected(qtbot: QtBot):
    view_model = AnnotationViewModel()
    view_model.annotation_view_state = MOCK_ANNOTATION_STATE
    plot = AnnotationPlot(view_model)
    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)
    plot.populate(MOCK_ANNOTATION_STATE)
    plot.dragging_node = MOCK_ANNOTATION_STATE.nodes[3]

    event = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    plot.mouseReleaseEvent(event)  # type: ignore[arg-type]

    node_views = _node_views(plot)
    assert len(node_views) == 1
    assert node_views[0].selected_node == 3


def test_mouse_release_without_drag_keeps_selection(qtbot: QtBot):
    plot = AnnotationPlot(AnnotationViewModel())
    plot.selected_node = 1

    event = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    plot.mouseReleaseEvent(event)  # type: ignore[arg-type]

    assert plot.selected_node == 1


@pytest.mark.parametrize("key", [Qt.Key.Key_Delete, Qt.Key.Key_Backspace])
def test_delete_keys_are_accepted_when_node_selected(qtbot: QtBot, key: Qt.Key):
    view_model = AnnotationViewModel()
    view_model.delete_node = lambda x: None

    plot = AnnotationPlot(view_model)
    event = _key_event(key)
    event.ignore()

    plot.selected_node = 0
    plot.keyPressEvent(event)

    assert event.isAccepted()


def test_other_keys_are_ignored(qtbot: QtBot):
    plot = AnnotationPlot(AnnotationViewModel())
    event = _key_event(Qt.Key.Key_A)
    event.accept()

    plot.keyPressEvent(event)

    assert not event.isAccepted()


def test_key_press_with_none_event_does_nothing(qtbot: QtBot):
    plot = AnnotationPlot(AnnotationViewModel())

    plot.keyPressEvent(None)


def _create_label_action(plot: AnnotationPlot) -> ContextMenuHintAction:
    return next(a for a in plot.actions() if isinstance(a, ContextMenuHintAction))


def _shown_plot(
    qtbot: QtBot, view_model: AnnotationViewModel
) -> tuple[AnnotationPlot, pg.GraphicsLayoutWidget]:
    plot = AnnotationPlot(view_model)
    layout = show_plot_in_layout(plot)
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)
    plot.getViewBox().setRange(xRange=(0.0, 4.0), yRange=(0.0, 2.0), padding=0)
    return plot, layout


def _record_create_label(view_model: AnnotationViewModel) -> list[tuple]:
    calls = []
    view_model.create_label_from_selection = (  # type: ignore[method-assign]
        lambda *args: calls.append(args)
    )
    return calls


def test_create_label_action_is_in_context_menu_with_shortcut(qtbot: QtBot):
    plot = AnnotationPlot(AnnotationViewModel())

    action = _create_label_action(plot)

    assert action in plot.getViewBox().menu.actions()
    assert action.shortcut() == QKeySequence("Ctrl+L")


def test_create_label_action_triggers_create_label_from_selection(qtbot: QtBot):
    view_model = AnnotationViewModel()
    calls = _record_create_label(view_model)
    plot = AnnotationPlot(view_model)
    plot.update_selection_region(1.0, 2.0)
    plot.selected_type = 1

    _create_label_action(plot).trigger()

    assert calls == [(1, 1.0, 3.0)]


def test_right_click_stores_context_pos_and_ignores_event(qtbot: QtBot):
    plot, _layout = _shown_plot(qtbot, AnnotationViewModel())
    scene_pos = plot.getViewBox().mapViewToScene(QPointF(1.0, 1.5))

    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        scene_pos,
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    event.scenePos = lambda: scene_pos
    plot.mousePressEvent(event)  # type: ignore[arg-type]

    assert plot.context_pos is not None
    assert plot.context_pos.x() == pytest.approx(1.0)
    assert plot.context_pos.y() == pytest.approx(1.5)
    assert not event.isAccepted()
    assert plot.dragging_node is None


def test_context_menu_close_clears_context_pos_after_event_loop(qtbot: QtBot):
    plot = AnnotationPlot(AnnotationViewModel())
    plot.context_pos = QPointF(1.0, 1.0)

    plot.getViewBox().menu.aboutToHide.emit()

    assert plot.context_pos is not None
    qtbot.waitUntil(lambda: plot.context_pos is None, timeout=1000)


def test_focus_out_unselects_node(qtbot: QtBot):
    plot, _layout = _shown_plot(qtbot, AnnotationViewModel())
    plot.selected_node = 2
    plot.populate(MOCK_ANNOTATION_STATE)

    plot.focusOutEvent(QFocusEvent(QEvent.Type.FocusOut))

    assert plot.selected_node is None
    assert _node_views(plot)[0].selected_node is None


def test_focus_out_without_selection_keeps_none(qtbot: QtBot):
    plot = AnnotationPlot(AnnotationViewModel())

    plot.focusOutEvent(QFocusEvent(QEvent.Type.FocusOut))

    assert plot.selected_node is None


def test_mouse_moved_inside_view_selects_tier_under_cursor(qtbot: QtBot):
    plot, _layout = _shown_plot(qtbot, AnnotationViewModel())

    plot.on_mouse_moved(plot.getViewBox().mapViewToScene(QPointF(1.0, 1.5)))

    assert plot.selected_type == 1


def test_mouse_moved_outside_view_clears_tier_and_hides_indicator(qtbot: QtBot):
    plot, _layout = _shown_plot(qtbot, AnnotationViewModel())
    plot.update_selection_region(1.0, 1.0)
    plot.on_mouse_moved(plot.getViewBox().mapViewToScene(QPointF(1.0, 0.5)))

    plot.on_mouse_moved(plot.getViewBox().mapViewToScene(QPointF(1.0, 50.0)))

    assert plot.selected_type is None
    assert not plot.tier_selection.left_bar.isVisible()
    assert not plot.tier_selection.right_bar.isVisible()


def test_mouse_moved_with_selection_shows_indicator_on_tier(qtbot: QtBot):
    plot, _layout = _shown_plot(qtbot, AnnotationViewModel())
    plot.update_selection_region(1.0, 2.0)

    plot.on_mouse_moved(plot.getViewBox().mapViewToScene(QPointF(2.0, 1.5)))

    left_x, left_y = plot.tier_selection.left_bar.getData()
    right_x, _ = plot.tier_selection.right_bar.getData()
    assert plot.tier_selection.left_bar.isVisible()
    assert list(left_x) == [1.0, 1.0]
    assert list(right_x) == [3.0, 3.0]
    assert list(left_y) == [1, 2]


def test_create_label_from_selection_without_selection_does_nothing(qtbot: QtBot):
    view_model = AnnotationViewModel()
    calls = _record_create_label(view_model)
    plot = AnnotationPlot(view_model)
    plot.selected_type = 0

    plot.create_label_from_selection()

    assert calls == []


def test_create_label_from_selection_without_tier_does_nothing(qtbot: QtBot):
    view_model = AnnotationViewModel()
    calls = _record_create_label(view_model)
    plot = AnnotationPlot(view_model)
    plot.update_selection_region(1.0, 2.0)

    plot.create_label_from_selection()

    assert calls == []


def test_create_label_from_selection_prefers_context_menu_tier(qtbot: QtBot):
    view_model = AnnotationViewModel()
    calls = _record_create_label(view_model)
    plot = AnnotationPlot(view_model)
    plot.update_selection_region(1.0, 2.0)
    plot.selected_type = 0
    plot.context_pos = QPointF(0.5, 2.5)

    plot.create_label_from_selection()

    assert calls == [(2, 1.0, 3.0)]
