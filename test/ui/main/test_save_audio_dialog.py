from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

import ui.document.document_view_model as dvm_module
from core.load_audio.entity.audio_signal import AudioSignal
from ui.document.document_view import DocumentView
from ui.document.document_view_model import DocumentViewModel
from ui.main.save_audio_dialog import SaveAudioDialog, SaveOptions, _default_filename


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


# --------------------------- _default_filename ---------------------------


def test_default_filename_appends_wav_extension():
    assert _default_filename("myclip") == "myclip.wav"


def test_default_filename_keeps_existing_wav_extension():
    assert _default_filename("myclip.wav") == "myclip.wav"


def test_default_filename_sanitizes_invalid_characters():
    assert _default_filename('foo:bar/baz*?"<>|') == "foo_bar_baz______.wav"


# --------------------------- dialog construction ---------------------------


def test_dialog_defaults_to_origin_directory_and_native_rate(
    qtbot: QtBot, document_view: DocumentView
):
    document_view.view_model.load_from_samples(
        AudioSignal(np.arange(5000, dtype=np.float64), 1000)
    )
    document_view.origin_path = "/home/user/audio/myfile.wav"

    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)

    assert dialog._default_path == "/home/user/audio/myfile.wav"
    assert dialog.path_edit.text() == "/home/user/audio/myfile.wav"
    assert dialog.rate_spin.value() == 1000
    assert dialog.scale_check.isChecked() is False


def test_dialog_defaults_to_home_directory_without_origin_path(
    qtbot: QtBot, document_view: DocumentView
):
    document_view.view_model.load_from_samples(
        AudioSignal(np.arange(5000, dtype=np.float64), 1000)
    )

    dialog = SaveAudioDialog(document_view, "clip name")
    qtbot.addWidget(dialog)

    assert dialog._default_path == str(Path.home() / "clip name.wav")


def test_dialog_creates_no_widgets_without_loaded_audio(
    qtbot: QtBot, document_view: DocumentView
):
    dialog = SaveAudioDialog(document_view, "nothing")
    qtbot.addWidget(dialog)

    assert hasattr(dialog, "path_edit") is False


def test_options_reflects_current_field_values(
    qtbot: QtBot, document_view: DocumentView
):
    document_view.view_model.load_from_samples(
        AudioSignal(np.arange(5000, dtype=np.float64), 1000)
    )
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)
    dialog.path_edit.setText("  /tmp/out.wav  ")
    dialog.rate_spin.setValue(22050)
    dialog.scale_check.setChecked(True)

    options = dialog.options()

    assert options == SaveOptions(path="/tmp/out.wav", target_fs=22050, scale=True)


def test_accept_is_blocked_when_path_is_blank(
    qtbot: QtBot, document_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    document_view.view_model.load_from_samples(
        AudioSignal(np.arange(5000, dtype=np.float64), 1000)
    )
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)
    dialog.path_edit.setText("   ")
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(True))
    )
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))

    dialog._on_accept()

    assert accepted == []
    assert warnings == [True]


def test_accept_succeeds_with_a_valid_path(qtbot: QtBot, document_view: DocumentView):
    document_view.view_model.load_from_samples(
        AudioSignal(np.arange(5000, dtype=np.float64), 1000)
    )
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)
    dialog.path_edit.setText("/tmp/real_path.wav")
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))

    dialog._on_accept()

    assert accepted == [True]


# --------------------------- get_options orchestration ---------------------------


def test_get_options_returns_none_when_dialog_cancelled(
    qtbot: QtBot, document_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    document_view.view_model.load_from_samples(
        AudioSignal(np.arange(5000, dtype=np.float64), 1000)
    )
    from PyQt6.QtWidgets import QDialog

    monkeypatch.setattr(
        SaveAudioDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    result = SaveAudioDialog.get_options(document_view, "myfile.wav")

    assert result is None


def test_get_options_returns_options_when_dialog_accepted(
    qtbot: QtBot, document_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    document_view.view_model.load_from_samples(
        AudioSignal(np.arange(5000, dtype=np.float64), 1000)
    )
    document_view.origin_path = "/tmp/myfile.wav"
    from PyQt6.QtWidgets import QDialog

    monkeypatch.setattr(
        SaveAudioDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )

    result = SaveAudioDialog.get_options(document_view, "myfile.wav")

    assert result.path == "/tmp/myfile.wav"
    assert result.target_fs == 1000
    assert result.scale is False
