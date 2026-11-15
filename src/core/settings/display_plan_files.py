from pathlib import Path

from core.settings.entity.tier_layout import TierLayout
from res.constants import (
    DISPLAY_SECTION,
    HIDDEN_TIERS_KEY,
    PLAN_KEY,
    PROJECT_FILE_NAME,
    TIER_ORDER_KEY,
)


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


def tier_layout_from_toml(contents: dict) -> TierLayout:
    """The tier layout stored under `[display]`. Anything absent or invalid is left
    out, as if the project said nothing about it"""
    section = contents.get(DISPLAY_SECTION)
    if not isinstance(section, dict):
        return TierLayout()
    return TierLayout(
        _names(section.get(HIDDEN_TIERS_KEY)), _names(section.get(TIER_ORDER_KEY))
    )


def _names(value: object) -> list[str]:
    if isinstance(value, list) and all(isinstance(name, str) for name in value):
        return value
    return []
