from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

import ui.document.document_view_model as dvm_module
from core.load_audio.entity.audio_signal import AudioSignal
from ui.document.document_view import DocumentView
from ui.document.document_view_model import DocumentViewModel
from ui.document.state.audio_channel_state import to_audio_state
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


def load_mono(document_view: DocumentView):
    document_view.view_model.load_from_samples(
        to_audio_state({0: AudioSignal(np.arange(5000, dtype=np.float64), 16000)})
    )


def load_stereo(document_view: DocumentView):
    document_view.view_model.load_from_samples(
        to_audio_state(
            {
                0: AudioSignal(np.arange(5000, dtype=np.float64), 16000),
                1: AudioSignal(np.arange(5000, dtype=np.float64) * 2, 16000),
            }
        )
    )


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
    load_mono(document_view)
    document_view.origin_path = "/home/user/audio/myfile.wav"

    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)

    assert dialog.directory_edit.text() == "/home/user/audio"
    assert dialog.filename_edit.text() == "myfile.wav"
    assert dialog.rate_dropdown.currentData() == 16000
    assert dialog.scale_check.isChecked() is False


def test_rate_dropdown_snaps_to_nearest_standard_rate(
    qtbot: QtBot, document_view: DocumentView
):
    document_view.view_model.load_from_samples(
        to_audio_state({0: AudioSignal(np.arange(5000, dtype=np.float64), 13000)})
    )

    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)

    assert dialog.rate_dropdown.currentData() == 12000


def test_dialog_defaults_to_home_directory_without_origin_path(
    qtbot: QtBot, document_view: DocumentView
):
    load_mono(document_view)

    dialog = SaveAudioDialog(document_view, "clip name")
    qtbot.addWidget(dialog)

    assert dialog.directory_edit.text() == str(Path.home())
    assert dialog.filename_edit.text() == "clip name.wav"


def test_dialog_creates_no_widgets_without_loaded_audio(
    qtbot: QtBot, document_view: DocumentView
):
    dialog = SaveAudioDialog(document_view, "nothing")
    qtbot.addWidget(dialog)

    assert hasattr(dialog, "directory_edit") is False
    assert hasattr(dialog, "filename_edit") is False


def test_options_reflects_current_field_values(
    qtbot: QtBot, document_view: DocumentView
):
    load_mono(document_view)
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)
    dialog.directory_edit.setText("  /tmp  ")
    dialog.filename_edit.setText("  out.wav  ")
    dialog.rate_dropdown.setCurrentIndex(dialog.rate_dropdown.findData(22050))
    dialog.scale_check.setChecked(True)

    options = dialog.options()

    assert options == SaveOptions(
        path="/tmp/out.wav", target_fs=22050, scale=True, channels=[0]
    )


def test_accept_is_blocked_when_directory_is_blank(
    qtbot: QtBot, document_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    load_mono(document_view)
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)
    dialog.directory_edit.setText("   ")
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(True))
    )
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))

    dialog._on_accept()

    assert accepted == []
    assert warnings == [True]


def test_accept_is_blocked_when_filename_is_blank(
    qtbot: QtBot, document_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    load_mono(document_view)
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)
    dialog.filename_edit.setText("   ")
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
    load_mono(document_view)
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)
    dialog.directory_edit.setText("/tmp")
    dialog.filename_edit.setText("real_path.wav")
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))

    dialog._on_accept()

    assert accepted == [True]


# --------------------------- stereo channel selection ---------------------------


def test_dialog_shows_channel_checkboxes_for_stereo_document(
    qtbot: QtBot, document_view: DocumentView
):
    load_stereo(document_view)

    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)

    assert hasattr(dialog, "channel_checks")


def test_dialog_hides_channel_checkboxes_for_mono_document(
    qtbot: QtBot, document_view: DocumentView
):
    load_mono(document_view)

    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)

    assert hasattr(dialog, "channel_checks") is False


def test_channel_checkboxes_default_from_both_active(
    qtbot: QtBot, document_view: DocumentView
):
    load_stereo(document_view)

    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)

    assert all(check.isChecked() for check in dialog.channel_checks)
    assert dialog.channel_status_label.text() == "Will be saved as a stereo file"


def test_channel_checkboxes_default_from_single_active(
    qtbot: QtBot, document_view: DocumentView
):
    load_stereo(document_view)
    document_view.view_model.toggle_channel_active(1)

    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)

    assert dialog.channel_checks[0].isChecked() is True
    assert dialog.channel_checks[1].isChecked() is False
    assert dialog.channel_status_label.text() == "Will be saved as mono (Channel 1)"


def test_channel_status_label_updates_on_toggle(
    qtbot: QtBot, document_view: DocumentView
):
    load_stereo(document_view)
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)

    dialog.channel_checks[0].setChecked(False)
    assert dialog.channel_status_label.text() == "Will be saved as mono (Channel 2)"

    dialog.channel_checks[1].setChecked(False)
    assert dialog.channel_status_label.text() == "Choose at least one channel to save"


def test_accept_is_blocked_when_no_channel_selected(
    qtbot: QtBot, document_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    load_stereo(document_view)
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)
    for check in dialog.channel_checks:
        check.setChecked(False)
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(True))
    )
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))

    dialog._on_accept()

    assert accepted == []
    assert warnings == [True]


def test_options_returns_both_channels_when_both_checked(
    qtbot: QtBot, document_view: DocumentView
):
    load_stereo(document_view)
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)

    assert dialog.options().channels == [0, 1]


def test_options_returns_single_channel_when_one_unchecked(
    qtbot: QtBot, document_view: DocumentView
):
    load_stereo(document_view)
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)
    dialog.channel_checks[1].setChecked(False)

    assert dialog.options().channels == [0]


def test_options_returns_primary_index_for_mono_document(
    qtbot: QtBot, document_view: DocumentView
):
    load_mono(document_view)
    dialog = SaveAudioDialog(document_view, "myfile.wav")
    qtbot.addWidget(dialog)

    assert dialog.options().channels == [0]


# --------------------------- get_options orchestration ---------------------------


def test_get_options_returns_none_when_dialog_cancelled(
    qtbot: QtBot, document_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    load_mono(document_view)
    from PyQt6.QtWidgets import QDialog

    monkeypatch.setattr(
        SaveAudioDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    result = SaveAudioDialog.get_options(document_view, "myfile.wav")

    assert result is None


def test_get_options_returns_options_when_dialog_accepted(
    qtbot: QtBot, document_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    load_mono(document_view)
    document_view.origin_path = "/tmp/myfile.wav"
    from PyQt6.QtWidgets import QDialog

    monkeypatch.setattr(
        SaveAudioDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )

    result = SaveAudioDialog.get_options(document_view, "myfile.wav")

    assert result.path == "/tmp/myfile.wav"
    assert result.target_fs == 16000
    assert result.scale is False
    assert result.channels == [0]
