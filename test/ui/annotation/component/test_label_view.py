import pyqtgraph as pg
from pytestqt.qtbot import QtBot

from ui.annotation.component.label_view import LabelView
from ui.annotation.state.label_view_state import LabelViewState


def test_label_view_stores_input_labels(qtbot: QtBot):
    plot = pg.PlotItem()
    labels = [
        LabelViewState((1.0, 0.5), (0.5, 0.25), "hello"),
        LabelViewState((2.0, 0.5), (2.0, 0.25), "world"),
    ]

    label_view = LabelView(labels, plot)

    assert label_view.labels == labels


def test_label_view_creates_text_item_per_label_with_correct_text_and_position(
    qtbot: QtBot,
):
    plot = pg.PlotItem()
    labels = [
        LabelViewState((1.0, 0.5), (0.5, 0.25), "hello"),
        LabelViewState((2.0, 0.5), (2.0, 1.0), "world"),
    ]

    label_view = LabelView(labels, plot)

    text_items = [
        child for child in label_view.childItems() if isinstance(child, pg.TextItem)
    ]
    assert len(text_items) == 2

    texts = {item.toPlainText() for item in text_items}
    assert texts == {"hello", "world"}

    positions = {(item.pos().x(), item.pos().y()) for item in text_items}
    assert positions == {(0.5, 0.25), (2.0, 1.0)}


def test_label_view_bounding_rect_matches_parent_plot_view_rect(qtbot: QtBot):
    plot = pg.PlotItem()
    view_rect = plot.getViewBox().viewRect()

    label_view = LabelView([], plot)

    assert label_view.boundingRect() == view_rect


def test_label_view_position_follows_parent_plot_view(qtbot: QtBot):
    plot = pg.PlotItem()
    view_rect = plot.getViewBox().viewRect()

    label_view = LabelView([], plot)

    assert label_view.pos().x() == view_rect.left()
    assert label_view.pos().y() == view_rect.bottom()
