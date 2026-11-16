import tomllib
from pathlib import Path

import pytest

from core.settings.load_display_plan import LoadDisplayPlan
from core.settings.save_display_plan import SaveDisplayPlan


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    return tmp_path


def read(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def test_load_returns_none_without_a_project_file(project_dir: Path):
    assert LoadDisplayPlan()(str(project_dir)) is None


def test_load_returns_none_when_project_has_no_plan(project_dir: Path):
    (project_dir / "phonlab.toml").write_text("")

    assert LoadDisplayPlan()(str(project_dir)) is None


def test_save_writes_plan_to_project_file(project_dir: Path):
    SaveDisplayPlan()(["waveform", "spectrogram"], str(project_dir))

    assert read(project_dir / "phonlab.toml") == {
        "display": {"plan": ["waveform", "spectrogram"]}
    }


def test_save_keeps_other_contents_of_project_file(project_dir: Path):
    (project_dir / "phonlab.toml").write_text('name = "demo"\n[display]\nother = 1\n')

    SaveDisplayPlan()(["waveform"], str(project_dir))

    assert read(project_dir / "phonlab.toml") == {
        "name": "demo",
        "display": {"other": 1, "plan": ["waveform"]},
    }


def test_load_reads_saved_plan(project_dir: Path):
    SaveDisplayPlan()(["waveform", "annotation"], str(project_dir))

    assert LoadDisplayPlan()(str(project_dir)) == ["waveform", "annotation"]


@pytest.mark.parametrize(
    "contents",
    [
        "not [valid toml",
        "display = 3",
        "[display]\nplan = 'waveform'",
        "[display]\nplan = [1]",
    ],
)
def test_load_ignores_malformed_files(project_dir: Path, contents: str):
    (project_dir / "phonlab.toml").write_text(contents)

    assert LoadDisplayPlan()(str(project_dir)) is None
