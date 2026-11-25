import pytest
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QWidget
from pytestqt.qtbot import QtBot

from ui.main.component.open_with_annotation_dialog import ask_open_with_annotation


@pytest.fixture
def parent(qtbot: QtBot) -> QWidget:
    widget = QWidget()
    qtbot.addWidget(widget)
    return widget


def answer_question(
    monkeypatch: pytest.MonkeyPatch, button: QMessageBox.StandardButton, asked: list
):
    def question(
        parent: object, title: str, text: str, *args: object, **kwargs: object
    ) -> QMessageBox.StandardButton:
        asked.append(text)
        return button

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))


def test_one_annotation_is_offered_by_name_and_returned_when_accepted(
    parent: QWidget, monkeypatch: pytest.MonkeyPatch
):
    asked: list[str] = []
    answer_question(monkeypatch, QMessageBox.StandardButton.Yes, asked)

    chosen = ask_open_with_annotation(parent, "/d/a.wav", ["/d/a.srt"])

    assert chosen == "/d/a.srt"
    assert asked == ["Open a.wav with its annotation, a.srt?"]


def test_the_sound_file_is_opened_alone_when_the_annotation_is_declined(
    parent: QWidget, monkeypatch: pytest.MonkeyPatch
):
    answer_question(monkeypatch, QMessageBox.StandardButton.No, [])

    assert ask_open_with_annotation(parent, "/d/a.wav", ["/d/a.srt"]) is None


def test_with_several_annotations_the_user_picks_one(
    parent: QWidget, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        staticmethod(lambda parent, title, label, items, *args: (items[1], True)),
    )

    chosen = ask_open_with_annotation(parent, "/d/a.wav", ["/d/a.TextGrid", "/d/a.eaf"])

    assert chosen == "/d/a.eaf"


def test_cancelling_the_choice_opens_the_sound_file_alone(
    parent: QWidget, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        staticmethod(lambda parent, title, label, items, *args: ("", False)),
    )

    assert (
        ask_open_with_annotation(parent, "/d/a.wav", ["/d/a.TextGrid", "/d/a.eaf"])
        is None
    )
