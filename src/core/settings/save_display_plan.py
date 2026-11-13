import tomli_w

from core.base.use_case_sync import UseCaseSync
from core.settings.display_plan_files import project_file_path
from core.settings.toml_file import read_toml
from res.constants import DISPLAY_SECTION, PLAN_KEY


class SaveDisplayPlan(UseCaseSync[None]):
    """Saves the display plan to a project's file, keeping its other contents"""

    def __call__(self, plan: list[str], project_dir: str) -> None:
        path = project_file_path(project_dir)
        contents = read_toml(path)
        section = contents.get(DISPLAY_SECTION)
        if not isinstance(section, dict):
            section = {}
        section[PLAN_KEY] = plan
        contents[DISPLAY_SECTION] = section

        with open(path, "wb") as f:
            tomli_w.dump(contents, f)
