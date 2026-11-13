from collections.abc import Callable, Generator, Iterable
from pathlib import Path

import tomli_w
from PyQt6.QtCore import pyqtSlot

from core.project.add_project_files import AddProjectFiles
from core.project.entity.project_import_result import ProjectImportResult
from core.project.rebuild_project import RebuildProject
from core.project.scan_project_files import scan_project_files
from core.settings.app_settings import settings
from core.settings.load_display_plan import LoadDisplayPlan
from core.settings.save_display_plan import SaveDisplayPlan
from res.constants import PROJECT_DATABASE_FILENAME
from ui.base.view_model import ViewModel
from ui.document.state.plot_layout_state import (
    PlotType,
    plot_names,
    plots_from_names,
)
from ui.main.state.project_import_state import (
    ProjectImportState,
    to_project_import_state,
)


class MainViewModel(ViewModel):
    def __init__(
        self,
        load_display_plan: LoadDisplayPlan,
        save_display_plan: SaveDisplayPlan,
        provide_add_project_files: Callable[[str], AddProjectFiles],
        provide_rebuild_project: Callable[[str], RebuildProject],
    ):
        super().__init__()
        self.load_display_plan_use_case = load_display_plan
        self.save_display_plan_use_case = save_display_plan

        self.dir_path: str | None = None
        self.provide_add_project_files = provide_add_project_files
        self.provide_rebuild_project = provide_rebuild_project

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

    def is_new_project(self) -> bool:
        """True if the project directory has no database yet"""
        return not (Path(self._project_dir()) / PROJECT_DATABASE_FILENAME).exists()

    def project_files(self) -> list[tuple[str, str, str | None]]:
        """(file_stem, audio_file, annotation_file) for each audio file in the project
        directory, where annotation_file is None if it has no TextGrid"""
        return [
            (file.file_stem, file.audio_path, file.textgrid_path)
            for file in scan_project_files(self._project_dir())
        ]

    def add_project_files(self):
        """Add files new to the project to its database: file stems that are not in it
        yet, and TextGrids of files whose annotation is empty"""
        dir_path = self._project_dir()
        files = scan_project_files(dir_path)
        self._launch_import(self.provide_add_project_files(dir_path)(files))

    def rebuild_project(self):
        """Read all TextGrids into a new project database, backing up the old one"""
        dir_path = self._project_dir()
        files = scan_project_files(dir_path)
        self._launch_import(self.provide_rebuild_project(dir_path)(files))

    def _project_dir(self) -> str:
        if self.dir_path is None:
            raise ValueError("Cannot update project because directory path is not set")
        return self.dir_path

    def _launch_import(self, task: Generator[ProjectImportResult, None, None]):
        @pyqtSlot(object)
        def on_success(result: ProjectImportResult):
            self.state_changed.emit(to_project_import_state(result))

        @pyqtSlot(object)
        def on_error(error: Exception):
            self.state_changed.emit(ProjectImportState(finished=True, error=str(error)))

        self.launch_task("project_import", task, on_success, on_error, only_once=True)
