from pathlib import Path

from PyQt6.QtWidgets import QComboBox
from pytestqt.qtbot import QtBot

from ui.main.component.open_path_dialog import OpenPathDialog


def make_dialog(qtbot: QtBot, directory: Path) -> OpenPathDialog:
    dialog = OpenPathDialog(None, "Open", str(directory), "Sound files (*.wav)")
    qtbot.addWidget(dialog)
    return dialog


def test_accepts_a_selected_directory(qtbot: QtBot, tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    dialog = make_dialog(qtbot, tmp_path)
    dialog.selectFile(str(project))

    dialog.accept()

    assert dialog.result() == OpenPathDialog.DialogCode.Accepted
    assert dialog.selectedFiles() == [str(project)]


def test_accepts_selected_files(qtbot: QtBot, tmp_path: Path):
    wav = tmp_path / "sound.wav"
    wav.write_bytes(b"")
    dialog = make_dialog(qtbot, tmp_path)
    dialog.selectFile(str(wav))

    dialog.accept()

    assert dialog.result() == OpenPathDialog.DialogCode.Accepted
    assert dialog.selectedFiles() == [str(wav)]


def test_shows_a_selected_directory_as_the_project_in_the_name_box(
    qtbot: QtBot, tmp_path: Path
):
    (tmp_path / "project").mkdir()
    dialog = make_dialog(qtbot, tmp_path)
    dialog.show()

    dialog.selectFile(str(tmp_path / "project"))

    assert dialog.name_edit is not None and dialog.name_edit.text() == "project"
    assert dialog.name_label is not None
    assert dialog.name_label.text().replace("&", "") == "Project:"


def test_labels_the_name_box_as_a_file_name_for_a_file(qtbot: QtBot, tmp_path: Path):
    (tmp_path / "project").mkdir()
    wav = tmp_path / "sound.wav"
    wav.write_bytes(b"")
    dialog = make_dialog(qtbot, tmp_path)
    dialog.show()
    dialog.selectFile(str(tmp_path / "project"))

    dialog.selectFile(str(wav))

    assert dialog.name_edit is not None and dialog.name_edit.text() == "sound.wav"
    assert dialog.name_label is not None
    assert dialog.name_label.text().replace("&", "") == "File name:"


def test_hides_the_file_type_filter(qtbot: QtBot, tmp_path: Path):
    dialog = make_dialog(qtbot, tmp_path)
    dialog.show()

    combo = dialog.findChild(QComboBox, "fileTypeCombo")

    assert combo is not None and combo.isHidden()
