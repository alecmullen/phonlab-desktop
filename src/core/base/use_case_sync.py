from abc import ABC, abstractmethod


class UseCaseSync[T](ABC):
    @abstractmethod
    def invoke(self) -> T:
        pass
