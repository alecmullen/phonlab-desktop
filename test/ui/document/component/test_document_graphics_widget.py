from pytestqt.qtbot import QtBot

from ui.document.component.document_graphics_widget import DocumentGraphicsWidget


def test_resizing_announces_the_new_size(qtbot: QtBot):
    widget = DocumentGraphicsWidget()
    qtbot.addWidget(widget)
    widget.resize(300, 200)
    widget.show()
    qtbot.waitExposed(widget)

    with qtbot.waitSignal(widget.resized, timeout=1000):
        widget.resize(500, 400)

    assert widget.viewport().height() == 400


def test_the_layout_has_its_new_size_by_the_time_the_signal_arrives(qtbot: QtBot):
    widget = DocumentGraphicsWidget()
    qtbot.addWidget(widget)
    widget.resize(300, 200)
    widget.show()
    qtbot.waitExposed(widget)
    heights: list[int] = []
    widget.resized.connect(lambda: heights.append(widget.viewport().height()))

    widget.resize(500, 400)

    assert heights[-1] == 400
