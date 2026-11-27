from typing import Any, cast

from bootstrap.use_case_factory_impl import UseCaseFactory
from core.annotation.add_tiers import AddTiers
from core.annotation.create_label import CreateLabel
from core.annotation.delete_node import DeleteNode
from core.annotation.list_tier_names import ListTierNames
from core.annotation.load_annotation import LoadAnnotation
from core.annotation.replace_in_tier import ReplaceInTier
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.annotation.search_tier import SearchTier
from core.annotation.update_label import UpdateLabel
from core.annotation.update_node import UpdateNode
from core.edit_audio.edit_audio import EditAudio
from core.import_metadata.import_metadata import ImportMetadata
from core.import_metadata.information_sources_file import SaveInformationSource
from core.import_metadata.match_metadata import MatchMetadata
from core.import_metadata.read_metadata_csv import ReadMetadataCsv
from core.import_words.import_words import ImportWords
from core.import_words.match_words import MatchWords
from core.import_words.save_unmatched_words import SaveUnmatchedWords
from core.import_words.word_source_file import SaveWordSource
from core.inspect_database.inspect_database import ListTables, ReadTable
from core.load_audio.load_audio import LoadAudio
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.parse_textgrid.write_textgrid import WriteTextGrid
from core.project.add_project_files import AddProjectFiles
from core.project.close_project import CloseProject
from core.project.rebuild_project import RebuildProject
from core.project_layout.infer_layout import InferLayout
from core.project_layout.project_layout_file import (
    LoadProjectLayout,
    SaveProjectLayout,
)
from core.project_layout.resolve_recordings import ResolveRecordings
from core.project_layout.scan_project_tree import ScanProjectTree
from core.project_layout.suggest_talker_names import SuggestTalkerNames
from core.read_tiers.preview_annotation_table import PreviewAnnotationTable
from core.save_audio.save_audio import SaveAudio
from core.settings.load_display_plan import LoadDisplayPlan
from core.settings.load_tier_layout import LoadTierLayout
from core.settings.save_display_plan import SaveDisplayPlan
from core.settings.save_tier_layout import SaveTierLayout
from core.spectrogram.compute_sgram import ComputeSpectrogram
from core.spectrogram.compute_sgram_mmap import ComputeSpectrogramMmap
from core.track_formants.track_formants import TrackFormants
from core.track_formants.warm_up_formants import WarmUpFormantTracking
from core.transform_audio.filter_audio import FilterAudio
from core.transform_audio.prep_audio import PrepAudio
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.repository.annotation_repository import DataAnnotationRepository
from data.base.database import SQLiteDatabase
from phonlab_project.metadata import MetadataTarget
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.tier_search_view_model import TierSearchViewModel
from ui.base.dependency_factory import ViewModelFactory
from ui.base.view_model import ViewModel
from ui.database_view.database_view_model import DatabaseViewModel
from ui.document.document_view_model import DocumentViewModel
from ui.main.main_view_model import MainViewModel
from ui.metadata_import.metadata_import_view_model import MetadataImportViewModel
from ui.project_layout.project_layout_view_model import ProjectLayoutViewModel
from ui.spectrogram.spectrogram_view_model import SpectrogramViewModel
from ui.waveform.audio_wave_view_model import AudioWaveViewModel
from ui.word_import.word_import_view_model import WordImportViewModel


class ViewModelFactoryImpl(ViewModelFactory):
    def __init__(self):
        self.database = SQLiteDatabase()
        self.annotation_datasource = AnnotationDataSource(self.database)
        self.data_annotation_repository = DataAnnotationRepository(
            self.annotation_datasource
        )

        self.dir_use_case_factories: dict[str, UseCaseFactory] = {}
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
        elif view_model_type is TierSearchViewModel:
            view_model = self.create_tier_search_view_model(*args, **kwargs)
        elif view_model_type is AudioWaveViewModel:
            view_model = self.create_audio_wave_view_model(*args, **kwargs)
        elif view_model_type is MainViewModel:
            view_model = self.create_main_view_model(*args, **kwargs)
        elif view_model_type is ProjectLayoutViewModel:
            view_model = self.create_project_layout_view_model(*args, **kwargs)
        elif view_model_type is MetadataImportViewModel:
            view_model = self.create_metadata_import_view_model(*args, **kwargs)
        elif view_model_type is WordImportViewModel:
            view_model = self.create_word_import_view_model(*args, **kwargs)
        elif view_model_type is DatabaseViewModel:
            view_model = self.create_database_view_model(*args, **kwargs)

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

    def close_project(self, dir_path: str) -> None:
        """Close the database of a project directory and forget it, so that opening
        the directory again connects to it anew"""
        use_case_factory = self.dir_use_case_factories.pop(dir_path, None)
        if use_case_factory is not None:
            use_case_factory.provide(CloseProject).run_sync()

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
            use_case_factory.provide(WriteTextGrid),
            use_case_factory.provide(LoadAnnotation),
            use_case_factory.provide(AddTiers),
            use_case_factory.provide(ListTierNames),
            file_stem,
        )

    def create_tier_search_view_model(
        self, dir_path: str | None = None
    ) -> TierSearchViewModel:
        use_case_factory = self.get_use_case_factory(dir_path)

        return TierSearchViewModel(
            use_case_factory.provide(SearchTier),
            use_case_factory.provide(ReplaceInTier),
            is_project=dir_path is not None,
        )

    def create_audio_wave_view_model(self, channel_idx: int) -> AudioWaveViewModel:
        return AudioWaveViewModel(channel_idx)

    def create_main_view_model(self) -> MainViewModel:
        use_case_factory = self.get_use_case_factory(None)

        return MainViewModel(
            use_case_factory.provide(LoadDisplayPlan),
            use_case_factory.provide(SaveDisplayPlan),
            use_case_factory.provide(LoadTierLayout),
            use_case_factory.provide(SaveTierLayout),
            use_case_factory.provide(WarmUpFormantTracking),
            lambda dir_path: self.get_use_case_factory(dir_path).provide(
                AddProjectFiles
            ),
            lambda dir_path: self.get_use_case_factory(dir_path).provide(
                RebuildProject
            ),
            self.close_project,
        )

    def create_project_layout_view_model(self, dir_path: str) -> ProjectLayoutViewModel:
        # These use cases only read the project's files, so they do not open (and so
        # do not create) the project database
        use_case_factory = self.get_use_case_factory(None)

        return ProjectLayoutViewModel(
            dir_path,
            use_case_factory.provide(ScanProjectTree),
            use_case_factory.provide(InferLayout),
            use_case_factory.provide(ResolveRecordings),
            use_case_factory.provide(LoadProjectLayout),
            use_case_factory.provide(SaveProjectLayout),
            use_case_factory.provide(SuggestTalkerNames),
            use_case_factory.provide(PreviewAnnotationTable),
        )

    def create_metadata_import_view_model(
        self, dir_path: str, csv_path: str, target: MetadataTarget | None = None
    ) -> MetadataImportViewModel:
        use_case_factory = self.get_use_case_factory(dir_path)

        return MetadataImportViewModel(
            dir_path,
            csv_path,
            use_case_factory.provide(ReadMetadataCsv),
            use_case_factory.provide(MatchMetadata),
            use_case_factory.provide(ImportMetadata),
            use_case_factory.provide(SaveInformationSource),
            target,
        )

    def create_word_import_view_model(
        self, dir_path: str, csv_path: str
    ) -> WordImportViewModel:
        use_case_factory = self.get_use_case_factory(dir_path)

        return WordImportViewModel(
            dir_path,
            csv_path,
            use_case_factory.provide(ReadMetadataCsv),
            use_case_factory.provide(MatchWords),
            use_case_factory.provide(ImportWords),
            use_case_factory.provide(ListTierNames),
            use_case_factory.provide(SaveUnmatchedWords),
            use_case_factory.provide(SaveWordSource),
        )

    def create_database_view_model(self, dir_path: str) -> DatabaseViewModel:
        use_case_factory = self.get_use_case_factory(dir_path)

        return DatabaseViewModel(
            use_case_factory.provide(ListTables), use_case_factory.provide(ReadTable)
        )
