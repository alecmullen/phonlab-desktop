from typing import Protocol


class LocalDatabase(Protocol):
    def connect(self, dir_path: str): ...
