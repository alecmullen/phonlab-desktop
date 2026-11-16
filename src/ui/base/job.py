from collections.abc import Callable, Generator
from dataclasses import dataclass


@dataclass
class Job[T]:
    """A task with the callbacks that receive its results.

    A job queued behind a running one waits its turn, unless `replace_pending`
    is set: then it takes the place of any jobs still waiting (the running one
    is not stopped), for work where only the latest request matters."""

    task: Generator[T, None, None]
    on_success: Callable
    on_error: Callable
    replace_pending: bool = False
