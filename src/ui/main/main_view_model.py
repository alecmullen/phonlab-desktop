import logging
from collections.abc import Callable, Generator, Iterable
from pathlib import Path

import tomli_w
from PyQt6.QtCore import pyqtSlot

from core.project.add_project_files import AddProjectFiles
from core.project.entity.project_file import ProjectFile
from core.project.entity.project_import_result import (
    ImportStage,
    ProjectImportResult,
)
from core.project.rebuild_project import RebuildProject
from core.project.scan_project_files import scan_project_files
from core.settings.app_settings import settings
from core.settings.entity.tier_layout import TierLayout
from core.settings.load_display_plan import LoadDisplayPlan
from core.settings.load_tier_layout import LoadTierLayout
from core.settings.save_display_plan import SaveDisplayPlan
from core.settings.save_tier_layout import SaveTierLayout
from core.track_formants.warm_up_formants import WarmUpFormantTracking
from res.constants import PROJECT_DATABASE_FILENAME
from ui.base.view_model import ViewModel
from ui.document.state.plot_layout_state import (
    PlotType,
    plot_names,
    plots_from_names,
)
from ui.main.state.openable_file import OpenableFile
from ui.main.state.project_import_state import (
    ProjectImportState,
    to_project_import_state,
)

logger = logging.getLogger(__name__)


class MainViewModel(ViewModel):
    def __init__(
        self,
        load_display_plan: LoadDisplayPlan,
        save_display_plan: SaveDisplayPlan,
        load_tier_layout: LoadTierLayout,
        save_tier_layout: SaveTierLayout,
        warm_up_formants: WarmUpFormantTracking,
        provide_add_project_files: Callable[[str], AddProjectFiles],
        provide_rebuild_project: Callable[[str], RebuildProject],
        close_project_database: Callable[[str], None],
    ):
        super().__init__()
        self.load_display_plan_use_case = load_display_plan
        self.save_display_plan_use_case = save_display_plan
        self.load_tier_layout_use_case = load_tier_layout
        self.save_tier_layout_use_case = save_tier_layout
        self.warm_up_formants_use_case = warm_up_formants

        self.dir_path: str | None = None
        self.provide_add_project_files = provide_add_project_files
        self.provide_rebuild_project = provide_rebuild_project
        self.close_project_database = close_project_database

    @property
    def display_plan(self) -> frozenset[PlotType]:
        """The plots every document shows: whichever the user last chose"""
        return plots_from_names(settings.display_plan)

    @property
    def hidden_tiers(self) -> list[str]:
        """The names of the annotation tiers every document leaves out"""
        return settings.hidden_tiers

    @property
    def tier_order(self) -> list[str]:
        """The names of the annotation tiers in the order every document shows them,
        bottom to top"""
        return settings.tier_order

    @property
    def tier_fonts(self) -> dict[str, str]:
        """The font family of the labels of each annotation tier, by tier name, in
        every document. A tier not named uses the default font"""
        return settings.tier_fonts

    def set_tier_fonts(self, tier_fonts: dict[str, str]):
        """Show the labels of each tier in its font for the rest of the session"""
        settings.tier_fonts = tier_fonts

    def set_tier_display(self, hidden_tiers: list[str], tier_order: list[str]):
        """Hide the `hidden_tiers` and show the others in the order of `tier_order`
        for the rest of the session"""
        settings.hidden_tiers = hidden_tiers
        settings.tier_order = tier_order

    def set_dir_path(self, dir_path: str | None):
        if dir_path == self.dir_path:
            return
        self.dir_path = dir_path

        # A project that has saved its window layout starts from it
        if dir_path is not None:
            names = self.load_display_plan_use_case(dir_path)
            if names is not None:
                settings.display_plan = plot_names(plots_from_names(names))

            # Tier names belong to a project, so never carry them over from another
            layout = self.load_tier_layout_use_case(dir_path)
            settings.hidden_tiers = layout.hidden_tiers
            settings.tier_order = layout.tier_order
            settings.tier_fonts = layout.tier_fonts

    def close_project(self):
        """Close the open project's database. Like `set_dir_path(None)`, it keeps the
        display plan and tier layout the project gave. Does nothing when no project
        is open"""
        if self.dir_path is None:
            return

        self.close_project_database(self.dir_path)
        self.dir_path = None

    def set_display_plan(self, plots: Iterable[PlotType]):
        """Make `plots` the display plan for the rest of the session"""
        settings.display_plan = plot_names(plots_from_names(plot_names(plots)))

    def save_window_layout(self):
        """Save the display plan and the tier layout in the project file, so the
        project opens with them next time"""
        if self.dir_path is None:
            raise ValueError("Cannot save window layout because no project is open")

        self.save_display_plan_use_case(settings.display_plan, self.dir_path)
        self.save_tier_layout_use_case(
            TierLayout(settings.hidden_tiers, settings.tier_order, settings.tier_fonts),
            self.dir_path,
        )

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

    def project_files(self) -> list[OpenableFile]:
        """(file_stem, audio_file, annotation_file, channel_files) for each recording
        in the project, where annotation_file is None if it has no TextGrid and
        channel_files lists the audio files of a recording stored as one file per
        channel"""
        root = Path(self._project_dir())
        return [
            OpenableFile(
                file.file_stem,
                file.audio_path,
                file.textgrid_path,
                tuple(
                    str(root / path)
                    for path in (
                        file.recording.channel_files.values() if file.recording else ()
                    )
                ),
            )
            for file in scan_project_files(str(root))
        ]

    def textgrid_for(self, file_stem: str) -> str | None:
        """The TextGrid in the project directory that belongs to file_stem, if any"""
        for stem, _, textgrid_file, _ in self.project_files():
            if stem == file_stem:
                return textgrid_file
        return None

    def add_project_files(self):
        """Add files new to the project to its database: file stems that are not in it
        yet, and TextGrids of files whose annotation is empty"""
        dir_path = self._project_dir()
        add_project_files = self.provide_add_project_files(dir_path)
        self._launch_import(self._import_steps(dir_path, add_project_files))

    def rebuild_project(self):
        """Read all TextGrids into a new project database, backing up the old one, and
        add again the information from the CSV files the project remembers"""
        dir_path = self._project_dir()
        rebuild_project = self.provide_rebuild_project(dir_path)
        self._launch_import(
            self._import_steps(dir_path, lambda files: rebuild_project(files, dir_path))
        )

    def _import_steps(
        self,
        dir_path: str,
        update: Callable[
            [list[ProjectFile]], Generator[ProjectImportResult, None, None]
        ],
    ) -> Generator[ProjectImportResult, None, None]:
        """Looks through the project's files and then runs `update` on them, in the
        background where the user is told what is going on from the start"""
        yield ProjectImportResult(stage=ImportStage.SCANNING)
        yield from update(scan_project_files(dir_path))

    def _project_dir(self) -> str:
        if self.dir_path is None:
            raise ValueError("Cannot update project because directory path is not set")
        return self.dir_path

    def warm_up_formant_tracking(self):
        """Prepare formant tracking in the background, so the first time the
        user asks for formants does not wait on it"""

        @pyqtSlot(object)
        def on_success(_result: None):
            pass

        @pyqtSlot(object)
        def on_error(error: Exception):
            # Harmless: formant tracking just warms up when it is first used
            logger.warning("Formant tracking warm-up failed: %s", error)

        self.launch_task(
            "warm_up_formants",
            self.warm_up_formants_use_case(),
            on_success,
            on_error,
            only_once=True,
        )

    def _launch_import(self, task: Generator[ProjectImportResult, None, None]):
        @pyqtSlot(object)
        def on_success(result: ProjectImportResult):
            self.state_changed.emit(to_project_import_state(result))

        @pyqtSlot(object)
        def on_error(error: Exception):
            self.state_changed.emit(ProjectImportState(finished=True, error=str(error)))

        self.launch_task("project_import", task, on_success, on_error, only_once=True)
