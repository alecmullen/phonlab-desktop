from pathlib import Path

from res.constants import DISPLAY_SECTION, PLAN_KEY, PROJECT_FILE_NAME


def project_file_path(project_dir: str) -> Path:
    return Path(project_dir) / PROJECT_FILE_NAME


def plan_from_toml(contents: dict) -> list[str] | None:
    """The display plan stored under `[display]`, or None if absent or invalid"""
    section = contents.get(DISPLAY_SECTION)
    if not isinstance(section, dict):
        return None
    plan = section.get(PLAN_KEY)
    if isinstance(plan, list) and all(isinstance(name, str) for name in plan):
        return plan
    return None
