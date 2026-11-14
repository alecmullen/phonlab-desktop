"""Builders that wire view models to injected collaborators for tests.

Each builder takes the collaborators as optional keyword arguments, so a test
only names the ones it cares about, e.g.

    view_model = make_document_view_model(save_audio=save_audio)

Anything left out gets a default: use cases that are cheap, pure and the thing
under test are the real ones; use cases that touch disk or run long
computations are mocks (see `support.mocks`).
"""

from typing import Any, cast

from support.annotation_repository import SeedableAnnotationRepository
from support.mocks import mock_use_case

from core.annotation.add_tiers import AddTiers
from core.annotation.clear_interval import ClearInterval
from core.annotation.create_label import CreateLabel
from core.annotation.delete_node import DeleteNode
from core.annotation.list_tier_names import ListTierNames
from core.annotation.load_annotation import LoadAnnotation
from core.annotation.update_label import UpdateLabel
from core.annotation.update_node import UpdateNode
from core.edit_audio.edit_audio import EditAudio
from core.load_audio.load_audio import LoadAudio
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.parse_textgrid.write_textgrid import WriteTextGrid
from core.project.add_project_files import AddProjectFiles
from core.project.rebuild_project import RebuildProject
from core.save_audio.save_audio import SaveAudio
from core.settings.load_display_plan import LoadDisplayPlan
from core.settings.save_display_plan import SaveDisplayPlan
from core.spectrogram.compute_sgram import ComputeSpectrogram
from core.spectrogram.compute_sgram_mmap import ComputeSpectrogramMmap
from core.track_formants.track_formants import TrackFormants
from core.transform_audio.filter_audio import FilterAudio
from core.transform_audio.prep_audio import PrepAudio
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.base.dependency_factory import ViewModelFactory
from ui.base.view_model import ViewModel
from ui.document.document_view_model import DocumentViewModel
from ui.main.main_view_model import MainViewModel
from ui.spectrogram.spectrogram_view_model import SpectrogramViewModel
from ui.waveform.audio_wave_view_model import AudioWaveViewModel


class StubViewModelFactory(ViewModelFactory):
    """Builds child view models from the builders above.

    Pass `overrides` to substitute a view model of a given type, usually a
    `mock_view_model`:

        factory = StubViewModelFactory({AnnotationViewModel: annotation_vm})
    """

    def __init__(
        self,
        overrides: dict[type[ViewModel], ViewModel] | None = None,
        **document_use_cases: Any,  # noqa: ANN401
    ):
        """`document_use_cases` are passed on to `make_document_view_model`
        for any `DocumentViewModel` this factory creates"""
        self.overrides = overrides or {}
        self.document_use_cases = document_use_cases

    def create[T: ViewModel](
        self,
        view_model_type: type[T],
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> T:
        view_model: ViewModel
        if view_model_type in self.overrides:
            view_model = self.overrides[view_model_type]
        elif view_model_type is DocumentViewModel:
            file_stem, dir_path = (*args, None, None)[:2]
            view_model = make_document_view_model(
                self,
                file_stem=kwargs.get("file_stem", file_stem),
                dir_path=kwargs.get("dir_path", dir_path),
                **self.document_use_cases,
            )
        elif view_model_type is SpectrogramViewModel:
            view_model = make_spectrogram_view_model()
        elif view_model_type is AnnotationViewModel:
            view_model = make_annotation_view_model()
        elif view_model_type is AudioWaveViewModel:
            view_model = AudioWaveViewModel(*args, **kwargs)
        elif view_model_type is MainViewModel:
            view_model = make_main_view_model(*args, **kwargs)
        else:
            raise TypeError(f"No stub provided for {view_model_type!s}")
        return cast(T, view_model)


def make_create_label(repository: SeedableAnnotationRepository) -> CreateLabel:
    return CreateLabel(ClearInterval(repository), repository)


def make_annotation_view_model(
    create_label: CreateLabel | None = None,
    update_label: UpdateLabel | None = None,
    update_node: UpdateNode | None = None,
    delete_node: DeleteNode | None = None,
    parse_text_grid: ParseTextGrid | None = None,
    write_text_grid: WriteTextGrid | None = None,
    load_annotation: LoadAnnotation | None = None,
    filestem: str | None = None,
    repository: SeedableAnnotationRepository | None = None,
    add_tiers: AddTiers | None = None,
    list_tier_names: ListTierNames | None = None,
) -> AnnotationViewModel:
    repository = repository or SeedableAnnotationRepository()
    return AnnotationViewModel(
        create_label or make_create_label(repository),
        update_label or UpdateLabel(repository),
        update_node or UpdateNode(repository),
        delete_node or DeleteNode(repository),
        parse_text_grid or ParseTextGrid(repository),
        write_text_grid or WriteTextGrid(),
        load_annotation or LoadAnnotation(repository),
        add_tiers or AddTiers(repository),
        list_tier_names or ListTierNames(repository),
        filestem,
    )


def make_main_view_model(
    repository: SeedableAnnotationRepository | None = None,
    load_display_plan: LoadDisplayPlan | None = None,
    save_display_plan: SaveDisplayPlan | None = None,
) -> MainViewModel:
    if load_display_plan is None:
        load_display_plan = mock_use_case(LoadDisplayPlan)
        load_display_plan.return_value = None
    repository = repository or SeedableAnnotationRepository()
    add_project_files = AddProjectFiles(repository, ParseTextGrid(repository))
    return MainViewModel(
        load_display_plan,
        save_display_plan or mock_use_case(SaveDisplayPlan),
        lambda _dir_path: add_project_files,
        lambda _dir_path: RebuildProject(repository, add_project_files),
    )


def make_spectrogram_view_model(
    track_formants: TrackFormants | None = None,
    prep_audio: PrepAudio | None = None,
    compute_spectrogram: ComputeSpectrogram | None = None,
    compute_spectrogram_mmap: ComputeSpectrogramMmap | None = None,
) -> SpectrogramViewModel:
    return SpectrogramViewModel(
        track_formants or mock_use_case(TrackFormants),
        prep_audio or mock_use_case(PrepAudio),
        compute_spectrogram or mock_use_case(ComputeSpectrogram),
        compute_spectrogram_mmap or mock_use_case(ComputeSpectrogramMmap),
    )


def make_document_view_model(
    view_model_factory: ViewModelFactory | None = None,
    edit_audio: EditAudio | None = None,
    load_audio: LoadAudio | None = None,
    prep_audio: PrepAudio | None = None,
    filter_audio: FilterAudio | None = None,
    save_audio: SaveAudio | None = None,
    file_stem: str | None = None,
    dir_path: str | None = None,
) -> DocumentViewModel:
    return DocumentViewModel(
        view_model_factory or StubViewModelFactory(),
        edit_audio or EditAudio(),
        load_audio or mock_use_case(LoadAudio),
        prep_audio or PrepAudio(),
        filter_audio or FilterAudio(),
        save_audio or mock_use_case(SaveAudio),
        file_stem,
        dir_path,
    )
