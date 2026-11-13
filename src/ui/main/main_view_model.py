from collections.abc import Iterable
from pathlib import Path

import tomli_w

from core.settings.app_settings import settings
from core.settings.load_display_plan import LoadDisplayPlan
from core.settings.save_display_plan import SaveDisplayPlan
from ui.base.view_model import ViewModel
from ui.document.state.plot_layout_state import (
    PlotType,
    plot_names,
    plots_from_names,
)


class MainViewModel(ViewModel):
    def __init__(
        self,
        load_display_plan: LoadDisplayPlan,
        save_display_plan: SaveDisplayPlan,
    ):
        super().__init__()
        self.load_display_plan_use_case = load_display_plan
        self.save_display_plan_use_case = save_display_plan

        self.dir_path: str | None = None

    @property
    def display_plan(self) -> frozenset[PlotType]:
        """The plots every document shows: whichever the user last chose"""
        return plots_from_names(settings.display_plan)

    def set_dir_path(self, dir_path: str | None):
        if dir_path == self.dir_path:
            return
        self.dir_path = dir_path

        # A project that has saved its window layout starts from it
        if dir_path is not None:
            names = self.load_display_plan_use_case(dir_path)
            if names is not None:
                settings.display_plan = plot_names(plots_from_names(names))

    def set_display_plan(self, plots: Iterable[PlotType]):
        """Make `plots` the display plan for the rest of the session"""
        settings.display_plan = plot_names(plots_from_names(plot_names(plots)))

    def save_window_layout(self):
        """Save the display plan in the project file, so the project opens
        with it next time"""
        if self.dir_path is None:
            raise ValueError("Cannot save window layout because no project is open")

        self.save_display_plan_use_case(settings.display_plan, self.dir_path)

    def init_toml(self):
        if self.dir_path is None:
            raise ValueError(
                "Cannot initialize project because directory path is not set"
            )

        with open(Path(self.dir_path) / "phonlab.toml", "wb") as f:
            tomli_w.dump({}, f)
