import contextlib
import importlib.util
import logging
import os
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import pytest

PHONLAB_DESKTOP_PATH = (
    Path(__file__).resolve().parent.parent / "src" / "phonlab_desktop.py"
)


def load_module(module_name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, PHONLAB_DESKTOP_PATH)
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
    return module


@pytest.fixture
def mock_librosa_load(monkeypatch: pytest.MonkeyPatch) -> list:
    import librosa

    calls = []

    def fake_load(path: object) -> tuple[None, None]:
        calls.append(path)
        return (None, None)

    monkeypatch.setattr(librosa, "load", fake_load)
    return calls


@contextlib.contextmanager
def patched_qapplication(fake_cls: type) -> Iterator[None]:
    """Patch QApplication only for the duration of the block.

    pytest-qt's own teardown hooks call the real QApplication.instance()
    after every test, so the fake class must not still be installed when
    the test function returns.
    """
    import PyQt6.QtWidgets as qtwidgets_module

    original = qtwidgets_module.QApplication
    qtwidgets_module.QApplication = fake_cls
    try:
        yield
    finally:
        qtwidgets_module.QApplication = original


@pytest.fixture
def fake_run_app_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[type, type, type]:
    class FakeQApplication:
        instances: ClassVar[list["FakeQApplication"]] = []

        def __init__(self, argv: list[str]):
            self.argv = argv
            self.exec_called = False
            FakeQApplication.instances.append(self)

        def exec(self) -> int:
            self.exec_called = True
            return 0

    class FakeMainWindow:
        instances: ClassVar[list["FakeMainWindow"]] = []

        def __init__(self):
            self.shown = False
            self.splash = None
            self.opened_files = None
            FakeMainWindow.instances.append(self)

        def show(self) -> None:
            self.shown = True

        def open_files(self, files: list[str]) -> None:
            self.opened_files = files

    class FakeSplash:
        instances: ClassVar[list["FakeSplash"]] = []

        def __init__(self, main_window: "FakeMainWindow"):
            self.main_window = main_window
            self.shown = False
            FakeSplash.instances.append(self)

        def show(self) -> None:
            self.shown = True

    import ui.main.main_window as main_window_module
    import ui.main.splash as splash_module

    monkeypatch.setattr(main_window_module, "MainWindow", FakeMainWindow)
    monkeypatch.setattr(splash_module, "ClickableSplash", FakeSplash)

    return FakeQApplication, FakeMainWindow, FakeSplash


def test_warmup_only_env_exits_before_main_block(
    monkeypatch: pytest.MonkeyPatch, mock_librosa_load: list
):
    monkeypatch.setenv("PHONLAB_WARMUP_ONLY", "1")

    with pytest.raises(SystemExit) as exc_info:
        load_module("phonlab_desktop_warmup_test")

    assert exc_info.value.code == 0


def test_missing_example_audio_is_logged_and_does_not_raise(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    import librosa

    def raise_not_found(path: object) -> None:
        raise FileNotFoundError(path)

    monkeypatch.setattr(librosa, "load", raise_not_found)
    monkeypatch.delenv("PHONLAB_WARMUP_ONLY", raising=False)

    with caplog.at_level(logging.ERROR):
        load_module("phonlab_desktop_missing_audio_test")

    assert any(
        "Example file not found" in record.getMessage() for record in caplog.records
    )


def test_frozen_executable_creates_numba_cache_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mock_librosa_load: list
):
    monkeypatch.delenv("PHONLAB_WARMUP_ONLY", raising=False)
    monkeypatch.delenv("NUMBA_CACHE_DIR", raising=False)
    fake_executable = tmp_path / "Phonlab.app" / "Contents" / "MacOS" / "Phonlab"
    fake_executable.parent.mkdir(parents=True)
    fake_executable.touch()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_executable))

    load_module("phonlab_desktop_frozen_test")

    expected_cache_dir = fake_executable.parent / "numba_cache"
    assert expected_cache_dir.is_dir()
    assert os.environ["NUMBA_CACHE_DIR"] == str(expected_cache_dir)


def test_run_app_shows_main_window_and_splash_and_starts_event_loop(
    monkeypatch: pytest.MonkeyPatch,
    mock_librosa_load: list,
    fake_run_app_dependencies: tuple[type, type, type],
):
    fake_app_cls, fake_main_window_cls, fake_splash_cls = fake_run_app_dependencies
    monkeypatch.delenv("PHONLAB_WARMUP_ONLY", raising=False)
    monkeypatch.setattr(sys, "argv", ["phonlab_desktop.py"])

    with patched_qapplication(fake_app_cls):
        load_module("__main__")

    assert len(fake_main_window_cls.instances) == 1
    main_window = fake_main_window_cls.instances[0]
    splash = fake_splash_cls.instances[0]

    assert main_window.shown is True
    assert splash.shown is True
    assert main_window.splash is splash
    assert main_window.opened_files is None
    assert fake_app_cls.instances[0].exec_called is True


def test_run_app_opens_files_passed_as_command_line_arguments(
    monkeypatch: pytest.MonkeyPatch,
    mock_librosa_load: list,
    fake_run_app_dependencies: tuple[type, type, type],
):
    fake_app_cls, fake_main_window_cls, _ = fake_run_app_dependencies
    monkeypatch.delenv("PHONLAB_WARMUP_ONLY", raising=False)
    monkeypatch.setattr(sys, "argv", ["phonlab_desktop.py", "a.wav", "b.wav"])

    with patched_qapplication(fake_app_cls):
        load_module("__main__")

    main_window = fake_main_window_cls.instances[0]
    assert main_window.opened_files == ["a.wav", "b.wav"]
