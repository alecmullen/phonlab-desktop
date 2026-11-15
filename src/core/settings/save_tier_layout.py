from core.base.use_case_sync import UseCaseSync
from core.settings.display_plan_files import project_file_path
from core.settings.entity.tier_layout import TierLayout
from core.settings.toml_file import write_toml_values
from res.constants import (
    DISPLAY_SECTION,
    HIDDEN_TIERS_KEY,
    TIER_FONTS_KEY,
    TIER_ORDER_KEY,
)


class SaveTierLayout(UseCaseSync[None]):
    """Saves how a project shows its annotation tiers to its file, keeping its other
    contents. An empty list or table is left out of the file"""

    def __call__(self, layout: TierLayout, project_dir: str) -> None:
        write_toml_values(
            project_file_path(project_dir),
            DISPLAY_SECTION,
            {
                HIDDEN_TIERS_KEY: layout.hidden_tiers or None,
                TIER_ORDER_KEY: layout.tier_order or None,
                TIER_FONTS_KEY: layout.tier_fonts or None,
            },
        )
