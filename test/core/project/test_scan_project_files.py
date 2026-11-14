from pathlib import Path

import pytest

from core.project.entity.project_file import ProjectFile
from core.project.scan_project_files import (
    is_audio_file,
    is_textgrid_file,
    scan_project_files,
)


@pytest.mark.parametrize("name", ["a.wav", "a.WAV", "a.Wav", "dir/a.wav"])
def test_is_audio_file_ignores_case(name: str):
    assert is_audio_file(name)


@pytest.mark.parametrize("name", ["a.txt", "a.wav.txt", "wav", "a.TextGrid"])
def test_is_audio_file_rejects_other_files(name: str):
    assert not is_audio_file(name)


@pytest.mark.parametrize("name", ["a.TextGrid", "a.textgrid", "a.TEXTGRID"])
def test_is_textgrid_file_ignores_case(name: str):
    assert is_textgrid_file(name)


def test_scan_pairs_each_audio_file_with_its_textgrid(tmp_path: Path):
    for name in ("a.wav", "a.TextGrid", "b.WAV", "b.textgrid", "c.wav"):
        (tmp_path / name).write_bytes(b"")

    files = scan_project_files(str(tmp_path))

    assert files == [
        ProjectFile("a", str(tmp_path / "a.wav"), str(tmp_path / "a.TextGrid")),
        ProjectFile("b", str(tmp_path / "b.WAV"), str(tmp_path / "b.textgrid")),
        ProjectFile("c", str(tmp_path / "c.wav"), None),
    ]


def test_scan_does_not_pair_textgrid_whose_name_merely_ends_like_the_stem(
    tmp_path: Path,
):
    (tmp_path / "a.wav").write_bytes(b"")
    (tmp_path / "xa.TextGrid").write_bytes(b"")

    [file] = scan_project_files(str(tmp_path))

    assert file.textgrid_path is None


def test_scan_ignores_other_files_and_textgrids_without_audio(tmp_path: Path):
    for name in ("notes.txt", "lonely.TextGrid", "phonlab.toml"):
        (tmp_path / name).write_bytes(b"")

    assert scan_project_files(str(tmp_path)) == []
