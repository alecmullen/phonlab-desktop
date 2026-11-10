from pathlib import Path

import pytest
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox
from pytestqt.qtbot import QtBot

from ui.document.component.save_textgrid_dialog import (
    SaveTextGridDialog,
    _default_filename,
)

# --------------------------- _default_filename ---------------------------


def test_default_filename_appends_textgrid_extension():
    assert _default_filename("myclip") == "myclip.TextGrid"


def test_default_filename_flattens_project_relative_stem():
    assert (
        _default_filename("session1/speaker2/clip") == "session1_speaker2_clip.TextGrid"
    )


def test_default_filename_sanitizes_invalid_characters():
    assert _default_filename('foo:bar/baz*?"<>|') == "foo_bar_baz______.TextGrid"


def test_default_filename_strips_surrounding_whitespace():
    assert _default_filename("  myclip  ") == "myclip.TextGrid"


# --------------------------- construction ---------------------------


def make_dialog(
    qtbot: QtBot,
    origin_path: str = "/home/user/audio/myfile.wav",
    file_stem: str = "myfile",
) -> SaveTextGridDialog:
    dialog = SaveTextGridDialog(origin_path, file_stem)
    qtbot.addWidget(dialog)
    return dialog


def test_dialog_defaults_to_origin_directory_and_filename(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    assert dialog.directory_edit.text() == "/home/user/audio"
    assert dialog.filename_edit.text() == "myfile.TextGrid"


def test_dialog_defaults_to_home_directory_without_origin_path(qtbot: QtBot):
    dialog = make_dialog(qtbot, origin_path="")

    assert dialog.directory_edit.text() == str(Path.home())


def test_dialog_offers_short_and_long_formats_defaulting_to_short(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    assert [
        dialog.tg_type_selector.itemData(i)
        for i in range(dialog.tg_type_selector.count())
    ] == ["short", "long"]
    assert dialog.tg_type_selector.currentData() == "short"


# --------------------------- options ---------------------------


def test_options_joins_directory_and_filename(qtbot: QtBot):
    dialog = make_dialog(qtbot)
    dialog.directory_edit.setText("  /data/out  ")
    dialog.filename_edit.setText("  result.TextGrid ")

    path, tg_type = dialog.options()

    assert path == str(Path("/data/out") / "result.TextGrid")
    assert tg_type == "short"


def test_options_returns_selected_format(qtbot: QtBot):
    dialog = make_dialog(qtbot)
    dialog.tg_type_selector.setCurrentIndex(1)

    assert dialog.options()[1] == "long"


# --------------------------- browse ---------------------------


def test_browse_directory_updates_directory_edit(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    dialog = make_dialog(qtbot)
    monkeypatch.setattr(
        QFileDialog,
        "getExistingDirectory",
        staticmethod(lambda *args, **kwargs: "/chosen/dir"),
    )

    dialog._browse_directory()

    assert dialog.directory_edit.text() == "/chosen/dir"


def test_browse_directory_keeps_directory_when_cancelled(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    dialog = make_dialog(qtbot)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", staticmethod(lambda *args, **kwargs: "")
    )

    dialog._browse_directory()

    assert dialog.directory_edit.text() == "/home/user/audio"


# --------------------------- accept ---------------------------


@pytest.mark.parametrize("field", ["directory_edit", "filename_edit"])
def test_accept_warns_and_stays_open_when_a_field_is_blank(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, field: str
):
    dialog = make_dialog(qtbot)
    getattr(dialog, field).setText("   ")
    warnings: list = []
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *args: warnings.append(args))
    )

    dialog._on_accept()

    assert len(warnings) == 1
    assert dialog.result() != QDialog.DialogCode.Accepted


def test_accept_closes_dialog_when_fields_are_filled(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    dialog._on_accept()

    assert dialog.result() == QDialog.DialogCode.Accepted


# --------------------------- get_options ---------------------------


def test_get_options_returns_options_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        SaveTextGridDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )

    options = SaveTextGridDialog.get_options("/home/user/a.wav", "a")

    assert options == (str(Path("/home/user") / "a.TextGrid"), "short")


def test_get_options_returns_none_when_rejected(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        SaveTextGridDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    assert SaveTextGridDialog.get_options("/home/user/a.wav", "a") is None
