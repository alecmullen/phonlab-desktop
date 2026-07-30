from abc import ABC, abstractmethod


class UseCase[T](ABC):

    def __init__(self, key: str):
        self.key = key

    @abstractmethod
    def invoke(self) -> T:
        pass
