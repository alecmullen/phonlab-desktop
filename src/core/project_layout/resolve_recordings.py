from core.base.use_case_sync import UseCaseSync
from phonlab_project.layout.import_report import ResolvedProject
from phonlab_project.layout.project_layout import ProjectLayout
from phonlab_project.layout.project_scan import ProjectScan
from phonlab_project.layout.resolve_recordings import resolve_recordings


class ResolveRecordings(UseCaseSync[ResolvedProject]):
    """Applies a layout to a scanned project, writing nothing (see
    `resolve_recordings`). Raises `TemplateError` if the layout's filename template
    is invalid."""

    def __call__(self, scan: ProjectScan, layout: ProjectLayout) -> ResolvedProject:
        return resolve_recordings(scan, layout)
