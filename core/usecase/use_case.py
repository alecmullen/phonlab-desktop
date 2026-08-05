from abc import ABC, abstractmethod


class UseCase[T](ABC):

    @abstractmethod
    def invoke(self) -> T:
        pass
