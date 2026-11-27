from core.base.use_case_sync import UseCaseSync
from phonlab_project.layout.project_scan import ProjectScan
from phonlab_project.layout.scan_project_tree import scan_project_tree


class ScanProjectTree(UseCaseSync[ProjectScan]):
    """Lists every file under a project directory without reading any of them
    (see `scan_project_tree`)"""

    def __call__(self, dir_path: str) -> ProjectScan:
        return scan_project_tree(dir_path)
