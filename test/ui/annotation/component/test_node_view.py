import pyqtgraph as pg
from pytestqt.qtbot import QtBot

from res.constants import NODE_H_MARGIN, NODE_V_MARGIN
from ui.annotation.component.node_view import NodeView
from ui.annotation.state.node_view_state import NodeViewState


def test_node_view_stores_input_nodes(qtbot: QtBot):
    plot = pg.PlotItem()
    nodes = [NodeViewState(1.0, [0, 1]), NodeViewState(2.0, [0])]

    node_view = NodeView(nodes, plot)

    assert node_view.nodes == nodes


def test_node_view_renders_symbol_for_each_node(qtbot: QtBot):
    plot = pg.PlotItem()
    nodes = [
        NodeViewState(1.0, [0, 1]),
        NodeViewState(2.0, [0]),
        NodeViewState(3.0, [1]),
        NodeViewState(3.5, [1, 3]),
    ]

    node_view = NodeView(nodes, plot)

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

    node_view = NodeView([NodeViewState(0.0, [0])], plot)

    expected = view_rect.adjusted(
        -NODE_H_MARGIN, -NODE_V_MARGIN, NODE_H_MARGIN, NODE_V_MARGIN
    )
    assert node_view.boundingRect() == expected


def test_node_view_position_follows_parent_plot_view(qtbot: QtBot):
    plot = pg.PlotItem()
    view_rect = plot.getViewBox().viewRect()

    node_view = NodeView([NodeViewState(0.0, [0])], plot)

    assert node_view.pos().x() == view_rect.left()
    assert node_view.pos().y() == view_rect.bottom()
