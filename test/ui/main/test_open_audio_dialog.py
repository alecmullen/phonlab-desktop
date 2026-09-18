from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from PyQt6.QtWidgets import QDialog, QMessageBox
from pytestqt.qtbot import QtBot

from ui.main.open_audio_dialog import (
    OpenAudioDialog,
    _channel_label,
    _mono_options,
)


@pytest.fixture
def mono_wav(tmp_path: Path) -> str:
    path = tmp_path / "mono.wav"
    sf.write(str(path), np.linspace(-1, 1, 1000, dtype=np.float32), 16000)
    return str(path)


@pytest.fixture
def stereo_distinct_wav(tmp_path: Path) -> str:
    t = np.linspace(0, 1, 8000, dtype=np.float32)
    left = np.sin(2 * np.pi * 440 * t)
    right = np.sin(2 * np.pi * 220 * t)
    path = tmp_path / "stereo_distinct.wav"
    sf.write(str(path), np.stack([left, right], axis=1), 8000)
    return str(path)


@pytest.fixture
def stereo_duplicate_wav(tmp_path: Path) -> str:
    t = np.linspace(0, 1, 8000, dtype=np.float32)
    left = np.sin(2 * np.pi * 440 * t)
    path = tmp_path / "stereo_duplicate.wav"
    sf.write(str(path), np.stack([left, left], axis=1), 8000)
    return str(path)


@pytest.fixture
def three_channel_wav(tmp_path: Path) -> str:
    t = np.linspace(0, 1, 8000, dtype=np.float32)
    left = np.sin(2 * np.pi * 440 * t)
    right = np.sin(2 * np.pi * 220 * t)
    path = tmp_path / "three_channel.wav"
    sf.write(str(path), np.stack([left, right, left * 0.5], axis=1), 8000)
    return str(path)


# --------------------------- pure helpers ---------------------------


def test_channel_label_uses_left_right_names_for_multichannel_pair():
    assert _channel_label(0, native_channels=2) == "Channel 1 (Left)"
    assert _channel_label(1, native_channels=2) == "Channel 2 (Right)"


def test_channel_label_uses_generic_numbering_beyond_two_channels():
    assert _channel_label(2, native_channels=3) == "Channel 3"


def test_channel_label_uses_generic_numbering_for_single_channel():
    assert _channel_label(0, native_channels=1) == "Channel 1"


def test_mono_options_returns_single_retained_channel():
    options = _mono_options()

    assert options.channel_mode == "mono"
    assert options.retained_channels == [0]
    assert options.primary_channel == 0


# --------------------------- dialog construction ---------------------------


def test_mono_file_preselects_mono_and_disables_other_modes(
    qtbot: QtBot, mono_wav: str
):
    dialog = OpenAudioDialog(mono_wav)
    qtbot.addWidget(dialog)

    assert dialog.is_valid is True
    assert dialog.native_channels == 1
    assert dialog.mono_radio.isChecked() is True
    assert dialog.stereo_radio.isEnabled() is False
    assert dialog.multichannel_radio.isEnabled() is False
    assert dialog.build_options() == _mono_options()


def test_stereo_file_preselects_stereo_and_enables_stereo_mode(
    qtbot: QtBot, stereo_distinct_wav: str
):
    dialog = OpenAudioDialog(stereo_distinct_wav)
    qtbot.addWidget(dialog)

    assert dialog.native_channels == 2
    assert dialog.stereo_radio.isChecked() is True
    assert dialog.stereo_radio.isEnabled() is True
    assert dialog.multichannel_radio.isEnabled() is False
    items = [
        dialog.primary_channel_combo.itemText(i)
        for i in range(dialog.primary_channel_combo.count())
    ]
    assert items == ["Channel 1 (Left)", "Channel 2 (Right)"]


def test_three_channel_file_preselects_multichannel(
    qtbot: QtBot, three_channel_wav: str
):
    dialog = OpenAudioDialog(three_channel_wav)
    qtbot.addWidget(dialog)

    assert dialog.native_channels == 3
    assert dialog.multichannel_radio.isChecked() is True
    assert dialog.multichannel_radio.isEnabled() is True
    candidates = [
        dialog.primary_channel_combo.itemData(i)
        for i in range(dialog.primary_channel_combo.count())
    ]
    assert candidates == [0, 1, 2]
    assert dialog.build_options().retained_channels == [0, 1, 2]


def test_switching_channel_mode_preserves_selected_primary_channel(
    qtbot: QtBot, three_channel_wav: str
):
    dialog = OpenAudioDialog(three_channel_wav)
    qtbot.addWidget(dialog)
    dialog.primary_channel_combo.setCurrentIndex(2)
    assert dialog.primary_channel_combo.currentData() == 2

    dialog.mono_radio.setChecked(True)

    assert dialog.primary_channel_combo.currentData() == 2
    assert dialog.build_options().channel_mode == "mono"
    assert dialog.build_options().retained_channels == [2]


def test_build_options_for_stereo_mode_retains_both_channels(
    qtbot: QtBot, stereo_distinct_wav: str
):
    dialog = OpenAudioDialog(stereo_distinct_wav)
    qtbot.addWidget(dialog)

    options = dialog.build_options()

    assert options.channel_mode == "stereo"
    assert options.retained_channels == [0, 1]
    assert options.primary_channel == 0


# --------------------------- get_options orchestration ---------------------------


def test_get_options_skips_dialog_for_single_channel_file(qtbot: QtBot, mono_wav: str):
    result = OpenAudioDialog.get_options(mono_wav)

    assert result == _mono_options()


def test_get_options_returns_none_when_dialog_is_cancelled(
    qtbot: QtBot, stereo_distinct_wav: str, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        OpenAudioDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    result = OpenAudioDialog.get_options(stereo_distinct_wav)

    assert result is None


def test_get_options_returns_dialog_choice_when_accepted(
    qtbot: QtBot, stereo_distinct_wav: str, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        OpenAudioDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )

    result = OpenAudioDialog.get_options(stereo_distinct_wav)

    assert result.channel_mode == "stereo"
    assert result.retained_channels == [0, 1]


def test_get_options_auto_selects_mono_for_duplicate_stereo_channels(
    qtbot: QtBot, stereo_duplicate_wav: str, monkeypatch: pytest.MonkeyPatch
):
    warnings = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: warnings.append(True)),
    )

    result = OpenAudioDialog.get_options(stereo_duplicate_wav)

    assert result == _mono_options()
    assert warnings == [True]
