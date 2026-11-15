from core.base.use_case_sync import UseCaseSync
from core.settings.display_plan_files import project_file_path
from core.settings.toml_file import write_toml_values
from res.constants import DISPLAY_SECTION, PLAN_KEY


class SaveDisplayPlan(UseCaseSync[None]):
    """Saves the display plan to a project's file, keeping its other contents"""

    def __call__(self, plan: list[str], project_dir: str) -> None:
        write_toml_values(
            project_file_path(project_dir), DISPLAY_SECTION, {PLAN_KEY: plan}
        )
