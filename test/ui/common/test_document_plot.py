import pyqtgraph as pg
import pytest
from PyQt6.QtCore import QPointF
from pytestqt.qtbot import QtBot

from ui.common.document_plot import DocumentPlot


class DocumentPlotHost(DocumentPlot):
    def __init__(self):
        DocumentPlot.__init__(self)


def test_cursor_controller_starts_with_cursor_control(qtbot: QtBot):
    plot = DocumentPlotHost()

    assert plot.has_cursor_control is True


def test_remove_cursor_control_clears_flag_and_starts_timer(qtbot: QtBot):
    plot = DocumentPlotHost()

    plot.remove_cursor_control()

    assert plot.has_cursor_control is False
    assert plot.cursor_control_timer.isActive() is True


def test_regain_cursor_control_sets_flag_true(qtbot: QtBot):
    plot = DocumentPlotHost()
    plot.remove_cursor_control()

    plot.regain_cursor_control()

    assert plot.has_cursor_control is True


def test_cursor_control_timer_automatically_regains_control(qtbot: QtBot):
    plot = DocumentPlotHost()

    plot.remove_cursor_control()
    assert plot.has_cursor_control is False

    with qtbot.waitSignal(plot.cursor_control_timer.timeout, timeout=1000):
        pass

    assert plot.has_cursor_control is True


def test_set_cursor_position_moves_line_and_removes_control(qtbot: QtBot):
    plot = DocumentPlotHost()

    plot.set_cursor_position(3.0)

    assert plot.cursor_line.value() == 3.0
    assert plot.has_cursor_control is False


def test_on_mouse_moved_updates_cursor_when_in_control(qtbot: QtBot):
    plot = DocumentPlotHost()
    layout = pg.GraphicsLayoutWidget()
    qtbot.addWidget(layout)
    layout.addItem(plot)
    layout.resize(400, 300)
    layout.show()
    qtbot.waitExposed(layout)
    scene_pos = plot.getViewBox().mapViewToScene(QPointF(0.75, 0.0))

    plot.on_mouse_moved(scene_pos)

    assert plot.cursor_line.value() == pytest.approx(0.75)


def test_set_mark_position_moves_line_and_sets_visibility(qtbot: QtBot):
    plot = DocumentPlotHost()

    assert plot.mark_line.isVisible() is False

    plot.set_mark_position(2.5, True)
    assert plot.mark_line.value() == 2.5
    assert plot.mark_line.isVisible() is True

    plot.set_mark_position(2.5, False)
    assert plot.mark_line.isVisible() is False


def test_update_selection_region_shows_region_for_positive_range(qtbot: QtBot):
    plot = DocumentPlotHost()

    plot.update_selection_region(1.0, 2.0)

    assert plot.selection_region.isVisible() is True
    assert list(plot.selection_region.getRegion()) == [1.0, 3.0]


@pytest.mark.parametrize("xrange", [0.0, -1.0])
def test_update_selection_region_hides_region_for_zero_or_negative_range(
    qtbot: QtBot, xrange: float
):
    plot = DocumentPlotHost()
    plot.update_selection_region(1.0, 2.0)

    plot.update_selection_region(1.0, xrange)

    assert plot.selection_region.isVisible() is False
