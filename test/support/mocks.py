"""Helpers for faking the collaborators that view models are injected with.

Mocks are built with `create_autospec`, so a test fails if it calls something
the real class doesn't have, or calls it with the wrong arguments.
"""

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, create_autospec

from PyQt6.QtCore import QObject, pyqtSignal

from ui.base.view_model import ViewModel


class _StateSignal(QObject):
    state_changed = pyqtSignal(object)


def mock_view_model[T: ViewModel](view_model_type: type[T]) -> T:
    """A stand-in for `view_model_type` that records the calls made to it.

    Its `state_changed` is a real signal, so a parent view model can subscribe
    to it and the test can `emit` states as if the child had produced them.
    """
    view_model = create_autospec(view_model_type, instance=True)
    signal = _StateSignal()
    view_model.state_changed = signal.state_changed
    view_model._state_signal = signal  # keep the QObject alive with the mock
    return view_model


def mock_use_case[T](use_case_type: type[T]) -> T:
    """A stand-in for an injected use case; set its `return_value` (or use `yields` for a
    `UseCase`), then read its calls back with `assert_called_once_with`."""
    return create_autospec(use_case_type, instance=True)


def spy_on_use_case[T](use_case: T) -> T:
    """Wrap a real use case so it still runs but its calls can be asserted."""
    return create_autospec(type(use_case), instance=True, wraps=use_case)


def yields(use_case: MagicMock, *values: Any) -> None:  # noqa: ANN401
    """Make a `UseCase` mock return a fresh generator of `values` per call"""

    def make_task(*args: object, **kwargs: object) -> Iterator:
        return iter(values)

    use_case.side_effect = make_task
