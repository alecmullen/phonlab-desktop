from typing import Any, cast

from bootstrap.use_case_factory_impl import UseCaseFactory
from core.annotation.create_label import CreateLabel
from core.annotation.delete_node import DeleteNode
from core.annotation.load_annotation import LoadAnnotation
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.annotation.update_label import UpdateLabel
from core.annotation.update_node import UpdateNode
from core.edit_audio.edit_audio import EditAudio
from core.load_audio.load_audio import LoadAudio
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.save_audio.save_audio import SaveAudio
from core.spectrogram.compute_sgram import ComputeSpectrogram
from core.spectrogram.compute_sgram_mmap import ComputeSpectrogramMmap
from core.track_formants.track_formants import TrackFormants
from core.transform_audio.filter_audio import FilterAudio
from core.transform_audio.prep_audio import PrepAudio
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.repository.annotation_repository import DataAnnotationRepository
from data.base.database import SQLiteDatabase
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.base.dependency_factory import ViewModelFactory
from ui.base.view_model import ViewModel
from ui.document.document_view_model import DocumentViewModel
from ui.main.main_view_model import MainViewModel
from ui.spectrogram.spectrogram_view_model import SpectrogramViewModel
from ui.waveform.audio_wave_view_model import AudioWaveViewModel


class ViewModelFactoryImpl(ViewModelFactory):
    def __init__(self):
        self.database = SQLiteDatabase()
        self.annotation_datasource = AnnotationDataSource(self.database)
        self.data_annotation_repository = DataAnnotationRepository(
            self.annotation_datasource
        )

        self.dir_use_case_factories: dict[str, UseCaseFactory]
        self.in_mem_use_case_factory = UseCaseFactory(InMemAnnotationRepository())

    def create[T: ViewModel](
        self,
        view_model_type: type[T],
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> T:
        view_model = None
        if view_model_type is DocumentViewModel:
            view_model = self.create_document_view_model(*args, **kwargs)
        elif view_model_type is SpectrogramViewModel:
            view_model = self.create_spectrogram_view_model(*args, **kwargs)
        elif view_model_type is AnnotationViewModel:
            view_model = self.create_annotation_view_model(*args, **kwargs)
        elif view_model_type is AudioWaveViewModel:
            view_model = self.create_audio_wave_view_model(*args, **kwargs)
        elif view_model_type is MainViewModel:
            view_model = self.create_main_view_model(*args, **kwargs)

        if view_model is None:
            raise TypeError(f"No provider method for {view_model_type!s} found")
        else:
            return cast(T, view_model)

    def get_use_case_factory(self, dir_path: str | None) -> UseCaseFactory:
        if dir_path is None:
            use_case_factory = self.in_mem_use_case_factory
        else:
            if dir_path in self.dir_use_case_factories:
                use_case_factory = self.dir_use_case_factories[dir_path]
            else:
                database = SQLiteDatabase()
                database.connect(dir_path)
                annotation_datasource = AnnotationDataSource(database)
                annotation_repository = DataAnnotationRepository(annotation_datasource)

                use_case_factory = UseCaseFactory(annotation_repository)
                self.dir_use_case_factories[dir_path] = use_case_factory

        return use_case_factory

    def create_document_view_model(
        self, file_stem: str | None = None, dir_path: str | None = None
    ) -> DocumentViewModel:
        use_case_factory = self.get_use_case_factory(dir_path)

        return DocumentViewModel(
            self,
            use_case_factory.provide(EditAudio),
            use_case_factory.provide(LoadAudio),
            use_case_factory.provide(PrepAudio),
            use_case_factory.provide(FilterAudio),
            use_case_factory.provide(SaveAudio),
            file_stem,
            dir_path,
        )

    def create_spectrogram_view_model(self) -> SpectrogramViewModel:
        use_case_factory = self.get_use_case_factory(None)

        return SpectrogramViewModel(
            use_case_factory.provide(TrackFormants),
            use_case_factory.provide(PrepAudio),
            use_case_factory.provide(ComputeSpectrogram),
            use_case_factory.provide(ComputeSpectrogramMmap),
        )

    def create_annotation_view_model(
        self, file_stem: str | None = None, dir_path: str | None = None
    ) -> AnnotationViewModel:
        use_case_factory = self.get_use_case_factory(dir_path)

        return AnnotationViewModel(
            use_case_factory.provide(CreateLabel),
            use_case_factory.provide(UpdateLabel),
            use_case_factory.provide(UpdateNode),
            use_case_factory.provide(DeleteNode),
            use_case_factory.provide(ParseTextGrid),
            use_case_factory.provide(LoadAnnotation),
            file_stem,
        )

    def create_audio_wave_view_model(self, channel_idx: int) -> AudioWaveViewModel:
        return AudioWaveViewModel(channel_idx)

    def create_main_view_model(self) -> MainViewModel:
        return MainViewModel()
