from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any


class UseCase[T](ABC):
    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Generator[T, None, None]:  # noqa: ANN401
        pass

    def run_sync(self, *args: Any, **kwargs: Any) -> T:  # noqa: ANN401
        return next(self(*args, **kwargs))
