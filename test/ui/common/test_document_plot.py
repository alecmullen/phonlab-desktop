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
