from pathlib import Path

import tomli_w
from platformdirs import PlatformDirs

from core.database.connect_local_database import ConnectLocalDatabase
from ui.base.view_model import ViewModel


class MainViewModel(ViewModel):
    def __init__(self, connect_local_database: ConnectLocalDatabase):
        super().__init__()
        self.dir_path: str | None = None
        self.connect_local_database = connect_local_database

    def set_dir_path(self, dir_path: str | None):
        self.dir_path = dir_path

        if dir_path is not None:
            self.connect_local_database(dir_path)
        else:
            path = PlatformDirs("Phonlab").user_data_dir
            self.connect_local_database(path)

    def init_toml(self):
        if self.dir_path is None:
            raise ValueError(
                "Cannot initialize project because directory path is not set"
            )

        with open(Path(self.dir_path) / "phonlab.toml", "wb") as f:
            tomli_w.dump({}, f)
