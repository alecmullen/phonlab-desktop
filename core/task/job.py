from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Job:
    task: Callable
    on_success: Callable
    on_error: Callable
