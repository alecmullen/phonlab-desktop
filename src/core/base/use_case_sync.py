from abc import ABC, abstractmethod
from typing import Any


class UseCaseSync[T](ABC):
    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> T:  # noqa: ANN401
        pass
