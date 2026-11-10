import pyqtgraph as pg
from PyQt6.QtCore import QRectF
from pytestqt.qtbot import QtBot

from ui.common.loading_overlay import LoadingOverlay


def make_plot(qtbot: QtBot) -> tuple[pg.GraphicsLayoutWidget, pg.PlotItem]:
    widget = pg.GraphicsLayoutWidget()
    plot = widget.addPlot()
    qtbot.addWidget(widget)
    widget.resize(600, 300)
    widget.show()
    qtbot.wait(50)
    return widget, plot


def count_spinner_pixels(widget: pg.GraphicsLayoutWidget) -> int:
    image = widget.grab().toImage()
    return sum(
        1
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).blue() > 150
    )


def test_overlay_starts_hidden(qtbot: QtBot):
    _, plot = make_plot(qtbot)

    overlay = LoadingOverlay(plot)

    assert overlay.isVisible() is False
    assert overlay.timer.isActive() is False


def test_show_starts_animation_and_hide_stops_it(qtbot: QtBot):
    _, plot = make_plot(qtbot)
    overlay = LoadingOverlay(plot)

    overlay.show()
    assert overlay.isVisible() is True
    assert overlay.timer.isActive() is True

    overlay.hide()
    assert overlay.isVisible() is False
    assert overlay.timer.isActive() is False


def test_rotate_advances_angle_and_wraps_at_360(qtbot: QtBot):
    _, plot = make_plot(qtbot)
    overlay = LoadingOverlay(plot)

    overlay.rotate()
    assert overlay.angle == 10

    overlay.angle = 355
    overlay.rotate()
    assert overlay.angle == 5


def test_bounding_rect_covers_the_view_box_in_pixels(qtbot: QtBot):
    _, plot = make_plot(qtbot)
    overlay = LoadingOverlay(plot)

    assert overlay.boundingRect() == plot.getViewBox().boundingRect()
    assert overlay.boundingRect().width() > 100


def test_resizing_view_box_updates_bounding_rect(qtbot: QtBot):
    widget, plot = make_plot(qtbot)
    overlay = LoadingOverlay(plot)
    before = QRectF(overlay.boundingRect())

    widget.resize(900, 500)
    qtbot.wait(50)

    assert overlay.boundingRect() == plot.getViewBox().boundingRect()
    assert overlay.boundingRect().width() > before.width()


def test_visible_overlay_draws_spinner(qtbot: QtBot):
    widget, plot = make_plot(qtbot)
    overlay = LoadingOverlay(plot)
    assert count_spinner_pixels(widget) == 0

    overlay.show()
    qtbot.wait(50)

    assert count_spinner_pixels(widget) > 0


def test_paint_without_painter_does_nothing(qtbot: QtBot):
    _, plot = make_plot(qtbot)

    LoadingOverlay(plot).paint(None, None, None)
