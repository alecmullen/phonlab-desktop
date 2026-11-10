from pathlib import Path

import tomli_w

from ui.base.view_model import ViewModel


class MainViewModel(ViewModel):
    def __init__(self):
        super().__init__()
        self.dir_path: str | None = None

    def set_dir_path(self, dir_path: str | None):
        self.dir_path = dir_path

    def init_toml(self):
        if self.dir_path is None:
            raise ValueError(
                "Cannot initialize project because directory path is not set"
            )

        with open(Path(self.dir_path) / "phonlab.toml", "wb") as f:
            tomli_w.dump({}, f)
