"""Builders that wire view models to injected collaborators for tests.

Each builder takes the collaborators as optional keyword arguments, so a test
only names the ones it cares about, e.g.

    view_model = make_document_view_model(save_audio=save_audio)

Anything left out gets a default: use cases that are cheap, pure and the thing
under test are the real ones; use cases that touch disk or run long
computations are mocks (see `support.mocks`).
"""

from typing import Any, cast

from support.annotation_repository import FakeAnnotationRepository
from support.mocks import mock_use_case

from core.annotation.create_label import CreateLabel
from core.annotation.delete_node import DeleteNode
from core.database.connect_local_database import ConnectLocalDatabase
from core.edit_audio.edit_audio import EditAudio
from core.load_audio.load_audio import LoadAudio
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.save_audio.save_audio import SaveAudio
from core.spectrogram.compute_sgram import ComputeSpectrogram
from core.spectrogram.compute_sgram_mmap import ComputeSpectrogramMmap
from core.track_formants.track_formants import TrackFormants
from core.transform_audio.filter_audio import FilterAudio
from core.transform_audio.prep_audio import PrepAudio
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.base.view_model import ViewModel
from ui.base.view_model_factory import ViewModelFactory
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
            view_model = make_document_view_model(self, **self.document_use_cases)
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


def make_annotation_view_model(
    create_label: CreateLabel | None = None,
    delete_node: DeleteNode | None = None,
    parse_text_grid: ParseTextGrid | None = None,
) -> AnnotationViewModel:
    return AnnotationViewModel(
        create_label or CreateLabel(),
        delete_node or DeleteNode(),
        parse_text_grid or ParseTextGrid(FakeAnnotationRepository()),
    )


def make_main_view_model(
    connect_local_database: ConnectLocalDatabase | None = None,
) -> MainViewModel:
    return MainViewModel(connect_local_database or mock_use_case(ConnectLocalDatabase))


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
) -> DocumentViewModel:
    return DocumentViewModel(
        view_model_factory or StubViewModelFactory(),
        edit_audio or EditAudio(),
        load_audio or mock_use_case(LoadAudio),
        prep_audio or PrepAudio(),
        filter_audio or FilterAudio(),
        save_audio or mock_use_case(SaveAudio),
    )
