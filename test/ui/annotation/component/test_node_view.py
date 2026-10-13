import pyqtgraph as pg
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from pytestqt.qtbot import QtBot

from res.constants import NODE_H_MARGIN, NODE_V_MARGIN
from ui.annotation.component.node_view import NodeView
from ui.annotation.state.annotation_node_state import (
    AnnotationNodeExtentState,
    AnnotationNodeState,
)


def test_node_view_stores_input_nodes(qtbot: QtBot):
    plot = pg.PlotItem()
    nodes = [
        AnnotationNodeState(
            0, 1.0, [AnnotationNodeExtentState(0), AnnotationNodeExtentState(1)]
        ),
        AnnotationNodeState(1, 2.0, [AnnotationNodeExtentState(1)]),
    ]

    node_view = NodeView(plot, nodes)

    assert node_view.nodes == nodes


def test_node_view_renders_symbol_for_each_node(qtbot: QtBot):
    plot = pg.PlotItem()
    nodes = [
        AnnotationNodeState(
            0, 1.0, [AnnotationNodeExtentState(0), AnnotationNodeExtentState(1)]
        ),
        AnnotationNodeState(
            1, 2.0, [AnnotationNodeExtentState(0, has_point_label=True)]
        ),
        AnnotationNodeState(2, 3.0, [AnnotationNodeExtentState(1)]),
        AnnotationNodeState(
            3, 3.5, [AnnotationNodeExtentState(1), AnnotationNodeExtentState(3)]
        ),
    ]

    node_view = NodeView(plot, nodes)

    plot_data_items = [
        child for child in node_view.childItems() if isinstance(child, pg.PlotDataItem)
    ]
    assert len(plot_data_items) == 1

    x_data, y_data = plot_data_items[0].getData()
    assert list(x_data) == [1.0, 2.0, 3.0, 3.5]
    assert list(y_data) == [0, 0, 1, 1]


def test_node_view_bounding_rect_expands_view_rect_by_margins(qtbot: QtBot):
    plot = pg.PlotItem()
    view_rect = plot.getViewBox().viewRect()

    node_view = NodeView(
        plot, [AnnotationNodeState(0, 0.0, [AnnotationNodeExtentState(0)])]
    )

    expected = view_rect.adjusted(
        -NODE_H_MARGIN, -NODE_V_MARGIN, NODE_H_MARGIN, NODE_V_MARGIN
    )
    assert node_view.boundingRect() == expected


def test_node_view_position_follows_parent_plot_view(qtbot: QtBot):
    plot = pg.PlotItem()
    view_rect = plot.getViewBox().viewRect()

    layout = pg.GraphicsLayoutWidget()
    layout.addItem(plot)
    layout.resize(400, 300)
    layout.show()

    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)

    node_view = NodeView(
        plot, [AnnotationNodeState(0, 0.0, [AnnotationNodeExtentState(0)])]
    )

    assert node_view.pos().x() == view_rect.left()
    assert node_view.pos().y() == view_rect.bottom()


def test_node_view_paint_draws_picture(qtbot: QtBot):
    plot = pg.PlotItem()
    node_view = NodeView(
        plot, [AnnotationNodeState(0, 1.0, [AnnotationNodeExtentState(0)])]
    )

    pixmap = QPixmap(50, 50)
    painter = QPainter(pixmap)
    node_view.paint(painter, None, None)
    node_view.paint(None, None, None)
    painter.end()


def _symbol_items(node_view: NodeView) -> list[pg.PlotDataItem]:
    return [c for c in node_view.childItems() if isinstance(c, pg.PlotDataItem)]


def _symbol_color(item: pg.PlotDataItem) -> QColor:
    return pg.mkColor(item.opts["symbolPen"])


def _pixel_color(node_view: NodeView, x: int, y: int) -> QColor:
    scale = 20
    image = QImage(100, 100, QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.scale(scale, scale)
    node_view.paint(painter, None, None)
    painter.end()
    return image.pixelColor(x, y)


def test_node_view_has_no_selection_by_default(qtbot: QtBot):
    node_view = NodeView(
        pg.PlotItem(), [AnnotationNodeState(0, 1.0, [AnnotationNodeExtentState(0)])]
    )

    assert node_view.selected_node is None


def test_node_view_without_selection_renders_all_symbols_blue(qtbot: QtBot):
    nodes = [
        AnnotationNodeState(0, 1.0, [AnnotationNodeExtentState(0)]),
        AnnotationNodeState(1, 2.0, [AnnotationNodeExtentState(0)]),
    ]

    items = _symbol_items(NodeView(pg.PlotItem(), nodes))

    assert len(items) == 1
    assert _symbol_color(items[0]) == pg.mkColor("b")


def test_node_view_selected_node_renders_separate_red_symbol(qtbot: QtBot):
    nodes = [
        AnnotationNodeState(0, 1.0, [AnnotationNodeExtentState(0)]),
        AnnotationNodeState(1, 2.0, [AnnotationNodeExtentState(0)]),
        AnnotationNodeState(2, 3.0, [AnnotationNodeExtentState(1)]),
    ]

    node_view = NodeView(pg.PlotItem(), nodes, selected_node=1)

    assert node_view.selected_node == 1
    by_color = {_symbol_color(item).name(): item for item in _symbol_items(node_view)}
    assert set(by_color) == {pg.mkColor("b").name(), pg.mkColor("r").name()}

    blue_x, blue_y = by_color[pg.mkColor("b").name()].getData()
    red_x, red_y = by_color[pg.mkColor("r").name()].getData()
    assert list(blue_x) == [1.0, 3.0]
    assert list(blue_y) == [0, 1]
    assert list(red_x) == [2.0]
    assert list(red_y) == [0]


def test_node_view_selected_node_not_in_nodes_renders_only_blue(qtbot: QtBot):
    nodes = [AnnotationNodeState(0, 1.0, [AnnotationNodeExtentState(0)])]

    items = _symbol_items(NodeView(pg.PlotItem(), nodes, selected_node=99))

    assert len(items) == 1
    assert _symbol_color(items[0]) == pg.mkColor("b")


def test_node_view_all_nodes_selected_renders_only_red_symbols(qtbot: QtBot):
    nodes = [AnnotationNodeState(5, 1.0, [AnnotationNodeExtentState(0)])]

    node_view = NodeView(pg.PlotItem(), nodes, selected_node=5)

    colors = {_symbol_color(item).name() for item in _symbol_items(node_view)}
    assert pg.mkColor("r").name() in colors


def test_node_view_paints_selected_node_line_red_and_others_blue(qtbot: QtBot):
    nodes = [
        AnnotationNodeState(0, 2.0, [AnnotationNodeExtentState(0)]),
        AnnotationNodeState(1, 4.0, [AnnotationNodeExtentState(0)]),
    ]
    # Lines are drawn from tier 0 to 1; picture is scaled 20x, so x=2 -> 40, x=4 -> 80.
    node_view = NodeView(pg.PlotItem(), nodes, selected_node=1)

    unselected = _pixel_color(node_view, 40, 10)
    selected = _pixel_color(node_view, 80, 10)

    assert unselected.blue() > 200 and unselected.red() < 50
    assert selected.red() > 200 and selected.blue() < 50


def test_node_view_paints_all_lines_blue_without_selection(qtbot: QtBot):
    nodes = [AnnotationNodeState(0, 2.0, [AnnotationNodeExtentState(0)])]

    color = _pixel_color(NodeView(pg.PlotItem(), nodes), 40, 10)

    assert color.blue() > 200 and color.red() < 50
