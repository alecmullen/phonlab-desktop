from core.base.use_case_sync import UseCaseSync
from core.settings.display_plan_files import project_file_path, tier_layout_from_toml
from core.settings.entity.tier_layout import TierLayout
from core.settings.toml_file import read_toml


class LoadTierLayout(UseCaseSync[TierLayout]):
    """Reads how a project shows its annotation tiers from its file. A project that
    says nothing shows every tier"""

    def __call__(self, project_dir: str) -> TierLayout:
        return tier_layout_from_toml(read_toml(project_file_path(project_dir)))
