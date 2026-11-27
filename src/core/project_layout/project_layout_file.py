from core.base.use_case_sync import UseCaseSync
from phonlab_project.corpus import adopt_corpus_description
from phonlab_project.layout.project_layout import ProjectLayout
from phonlab_project.layout.project_layout_file import load_layout, save_layout


class LoadProjectLayout(UseCaseSync[ProjectLayout | None]):
    """The layout saved in the project's phonlab.toml, or None if there is none (see
    `load_layout`)"""

    def __call__(self, dir_path: str) -> ProjectLayout | None:
        return load_layout(dir_path)


class SaveProjectLayout(UseCaseSync[None]):
    """Saves the layout in the project's phonlab.toml, keeping its other settings (see
    `save_layout`), along with the description of the corpus the folder has, if any (see
    `adopt_corpus_description`)"""

    def __call__(self, dir_path: str, layout: ProjectLayout) -> None:
        save_layout(dir_path, layout)
        adopt_corpus_description(dir_path)
