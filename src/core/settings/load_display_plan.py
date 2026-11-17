from core.base.use_case_sync import UseCaseSync
from core.settings.display_plan_files import plan_from_toml, project_file_path
from core.settings.toml_file import read_toml


class LoadDisplayPlan(UseCaseSync[list[str] | None]):
    """Reads the display plan (the names of the plots to show) saved in a
    project's file. Returns None if the project has none."""

    def __call__(self, project_dir: str) -> list[str] | None:
        return plan_from_toml(read_toml(project_file_path(project_dir)))
