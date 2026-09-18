import numpy as np
import pytest
from PyQt6.QtWidgets import QLabel
from pytestqt.qtbot import QtBot

import ui.document.document_view_model as dvm_module
from core.load_audio.entity.audio_signal import AudioSignal
from ui.document.document_view import DocumentView
from ui.document.document_view_model import DocumentViewModel
from ui.main.audio_info_dialog import AudioInfoDialog


class FakeAudioPlayer:
    def stop(self):
        pass

    class playback_poll:
        @staticmethod
        def connect(slot: object):
            pass


@pytest.fixture
def document_view(monkeypatch: pytest.MonkeyPatch) -> DocumentView:
    monkeypatch.setattr(dvm_module, "AudioPlayer", FakeAudioPlayer)
    vm = DocumentViewModel()
    vm.prep_audio_spectrogram = lambda: None
    return DocumentView(vm)


def label_texts(dialog: AudioInfoDialog) -> list[str]:
    return [label.text() for label in dialog.findChildren(QLabel)]


def test_shows_name_sample_rate_duration_and_amplitude(
    qtbot: QtBot, document_view: DocumentView
):
    document_view.view_model.load_from_samples(
        AudioSignal(np.array([-2.0, -1.0, 0.0, 1.0, 3.0]), 1000)
    )

    dialog = AudioInfoDialog(document_view, "mydoc.wav")
    qtbot.addWidget(dialog)

    texts = label_texts(dialog)
    assert "mydoc.wav" in texts
    assert "1000 Hz" in texts
    assert "0.005 s" in texts
    assert "-2 / 3" in texts


def test_shows_placeholder_values_when_no_audio_is_loaded(
    qtbot: QtBot, document_view: DocumentView
):
    dialog = AudioInfoDialog(document_view, "empty.wav")
    qtbot.addWidget(dialog)

    texts = label_texts(dialog)
    assert "empty.wav" in texts
    assert "0 Hz" in texts
    assert "0.000 s" in texts
    assert "Min / max amplitude:" in texts
    assert not any("/" in text and text != "Min / max amplitude:" for text in texts)


def test_show_info_static_helper_execs_dialog(
    qtbot: QtBot, document_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    document_view.view_model.load_from_samples(AudioSignal(np.array([1.0, 2.0]), 1000))
    exec_calls = []
    monkeypatch.setattr(AudioInfoDialog, "exec", lambda self: exec_calls.append(True))

    AudioInfoDialog.show_info(document_view, "mydoc.wav")

    assert exec_calls == [True]
