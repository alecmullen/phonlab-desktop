from collections.abc import Callable, Generator
from dataclasses import dataclass


@dataclass
class Job[T]:
    task: Generator[T, None, None]
    on_success: Callable
    on_error: Callable
