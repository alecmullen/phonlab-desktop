from pathlib import Path

import pytest

from ui.main.main_view_model import MainViewModel


def test_dir_path_defaults_to_none():
    assert MainViewModel().dir_path is None


def test_set_dir_path_stores_path():
    view_model = MainViewModel()

    view_model.set_dir_path("/some/dir")

    assert view_model.dir_path == "/some/dir"


def test_init_toml_raises_without_dir_path():
    with pytest.raises(ValueError):
        MainViewModel().init_toml()


def test_init_toml_creates_phonlab_toml_in_dir(tmp_path: Path):
    view_model = MainViewModel()
    view_model.set_dir_path(str(tmp_path))

    view_model.init_toml()

    assert (tmp_path / "phonlab.toml").is_file()
