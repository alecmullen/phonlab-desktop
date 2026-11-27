from core.base.use_case_sync import UseCaseSync
from phonlab_project.layout.import_report import LayoutSuggestion
from phonlab_project.layout.infer_layout import infer_layout
from phonlab_project.layout.project_layout import ChannelRole
from phonlab_project.layout.project_scan import ProjectScan


class InferLayout(UseCaseSync[LayoutSuggestion]):
    """Proposes a layout for a scanned project from the evidence in the file tree
    (see `infer_layout`)"""

    def __call__(
        self, scan: ProjectScan, channels: tuple[ChannelRole, ...] | None = None
    ) -> LayoutSuggestion:
        return infer_layout(scan, channels)
