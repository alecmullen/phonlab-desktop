from collections.abc import Callable, Generator
from dataclasses import dataclass


@dataclass
class Job[T]:
    """A task with the callbacks that receive its results.

    Jobs are added to the end of a queue, unless `replace_pending`
    is set: then it replaces the pending job (but not the running one)"""

    task: Generator[T, None, None]
    on_success: Callable
    on_error: Callable
    replace_pending: bool = False
