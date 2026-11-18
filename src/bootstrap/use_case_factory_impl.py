from typing import cast

from core.annotation.add_tiers import AddTiers
from core.annotation.clear_interval import ClearInterval
from core.annotation.create_label import CreateLabel
from core.annotation.delete_node import DeleteNode
from core.annotation.list_tier_names import ListTierNames
from core.annotation.load_annotation import LoadAnnotation
from core.annotation.replace_in_tier import ReplaceInTier
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.annotation.search_tier import SearchTier
from core.annotation.update_label import UpdateLabel
from core.annotation.update_node import UpdateNode
from core.edit_audio.edit_audio import EditAudio
from core.import_metadata.apply_information_sources import ApplyInformationSources
from core.import_metadata.import_metadata import ImportMetadata
from core.import_metadata.information_sources_file import (
    LoadInformationSources,
    SaveInformationSource,
)
from core.import_metadata.match_metadata import MatchMetadata
from core.import_metadata.read_metadata_csv import ReadMetadataCsv
from core.import_words.import_words import ImportWords
from core.import_words.match_words import MatchWords
from core.import_words.save_unmatched_words import SaveUnmatchedWords
from core.import_words.word_source_file import LoadWordSource, SaveWordSource
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


class UseCaseFactory:
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

        self.edit_audio = EditAudio()
        self.load_audio = LoadAudio()
        self.prep_audio = PrepAudio()
        self.filter_audio = FilterAudio()
        self.save_audio = SaveAudio()
        self.track_formants = TrackFormants()
        self.warm_up_formants = WarmUpFormantTracking()
        self.compute_sgram = ComputeSpectrogram()
        self.compute_sgram_mmap = ComputeSpectrogramMmap()
        self.clear_interval = ClearInterval(self.annotation_repository)
        self.create_label = CreateLabel(self.clear_interval, self.annotation_repository)
        self.update_label = UpdateLabel(self.annotation_repository)
        self.search_tier = SearchTier(self.annotation_repository)
        self.replace_in_tier = ReplaceInTier(self.update_label)
        self.update_node = UpdateNode(self.annotation_repository)
        self.delete_node = DeleteNode(self.annotation_repository)
        self.load_annotation = LoadAnnotation(self.annotation_repository)
        self.parse_textgrid = ParseTextGrid(self.annotation_repository)
        self.add_tiers = AddTiers(self.annotation_repository)
        self.list_tier_names = ListTierNames(self.annotation_repository)
        self.write_textgrid = WriteTextGrid()
        self.load_display_plan = LoadDisplayPlan()
        self.save_display_plan = SaveDisplayPlan()
        self.load_tier_layout = LoadTierLayout()
        self.save_tier_layout = SaveTierLayout()
        self.add_project_files = AddProjectFiles(
            self.annotation_repository, self.parse_textgrid
        )
        self.read_metadata_csv = ReadMetadataCsv()
        self.match_metadata = MatchMetadata(self.annotation_repository)
        self.import_metadata = ImportMetadata(self.annotation_repository)
        self.load_information_sources = LoadInformationSources()
        self.save_information_source = SaveInformationSource()
        self.match_words = MatchWords(self.annotation_repository)
        self.import_words = ImportWords(self.annotation_repository)
        self.save_unmatched_words = SaveUnmatchedWords()
        self.load_word_source = LoadWordSource()
        self.save_word_source = SaveWordSource()
        self.apply_information_sources = ApplyInformationSources(
            self.load_information_sources,
            self.read_metadata_csv,
            self.match_metadata,
            self.import_metadata,
            self.load_word_source,
            self.import_words,
        )
        self.rebuild_project = RebuildProject(
            self.annotation_repository,
            self.add_project_files,
            self.apply_information_sources,
        )
        self.close_project = CloseProject(self.annotation_repository)
        self.scan_project_tree = ScanProjectTree()
        self.infer_layout = InferLayout()
        self.resolve_recordings = ResolveRecordings()
        self.load_project_layout = LoadProjectLayout()
        self.save_project_layout = SaveProjectLayout()
        self.suggest_talker_names = SuggestTalkerNames()
        self.preview_annotation_table = PreviewAnnotationTable()
        self.list_tables = ListTables(self.annotation_repository)
        self.read_table = ReadTable(self.annotation_repository)

    def provide[T](
        self,
        use_case_type: type[T],
    ) -> T:
        use_case = None
        if use_case_type is EditAudio:
            use_case = self.edit_audio
        if use_case_type is LoadAudio:
            use_case = self.load_audio
        if use_case_type is PrepAudio:
            use_case = self.prep_audio
        if use_case_type is FilterAudio:
            use_case = self.filter_audio
        if use_case_type is SaveAudio:
            use_case = self.save_audio
        if use_case_type is TrackFormants:
            use_case = self.track_formants
        if use_case_type is WarmUpFormantTracking:
            use_case = self.warm_up_formants
        if use_case_type is ComputeSpectrogram:
            use_case = self.compute_sgram
        if use_case_type is ComputeSpectrogramMmap:
            use_case = self.compute_sgram_mmap
        if use_case_type is ClearInterval:
            use_case = self.clear_interval
        if use_case_type is CreateLabel:
            use_case = self.create_label
        if use_case_type is UpdateLabel:
            use_case = self.update_label
        if use_case_type is SearchTier:
            use_case = self.search_tier
        if use_case_type is ReplaceInTier:
            use_case = self.replace_in_tier
        if use_case_type is UpdateNode:
            use_case = self.update_node
        if use_case_type is DeleteNode:
            use_case = self.delete_node
        if use_case_type is LoadAnnotation:
            use_case = self.load_annotation
        if use_case_type is AddProjectFiles:
            use_case = self.add_project_files
        if use_case_type is RebuildProject:
            use_case = self.rebuild_project
        if use_case_type is CloseProject:
            use_case = self.close_project
        if use_case_type is AddTiers:
            use_case = self.add_tiers
        if use_case_type is ListTierNames:
            use_case = self.list_tier_names
        if use_case_type is ParseTextGrid:
            use_case = self.parse_textgrid
        if use_case_type is WriteTextGrid:
            use_case = self.write_textgrid
        if use_case_type is ScanProjectTree:
            use_case = self.scan_project_tree
        if use_case_type is InferLayout:
            use_case = self.infer_layout
        if use_case_type is ResolveRecordings:
            use_case = self.resolve_recordings
        if use_case_type is LoadProjectLayout:
            use_case = self.load_project_layout
        if use_case_type is SaveProjectLayout:
            use_case = self.save_project_layout
        if use_case_type is SuggestTalkerNames:
            use_case = self.suggest_talker_names
        if use_case_type is PreviewAnnotationTable:
            use_case = self.preview_annotation_table
        if use_case_type is ReadMetadataCsv:
            use_case = self.read_metadata_csv
        if use_case_type is MatchMetadata:
            use_case = self.match_metadata
        if use_case_type is ImportMetadata:
            use_case = self.import_metadata
        if use_case_type is LoadInformationSources:
            use_case = self.load_information_sources
        if use_case_type is SaveInformationSource:
            use_case = self.save_information_source
        if use_case_type is ApplyInformationSources:
            use_case = self.apply_information_sources
        if use_case_type is MatchWords:
            use_case = self.match_words
        if use_case_type is ImportWords:
            use_case = self.import_words
        if use_case_type is SaveUnmatchedWords:
            use_case = self.save_unmatched_words
        if use_case_type is LoadWordSource:
            use_case = self.load_word_source
        if use_case_type is SaveWordSource:
            use_case = self.save_word_source

        if use_case_type is ListTables:
            use_case = self.list_tables
        if use_case_type is ReadTable:
            use_case = self.read_table

        if use_case_type is LoadDisplayPlan:
            use_case = self.load_display_plan
        if use_case_type is SaveDisplayPlan:
            use_case = self.save_display_plan
        if use_case_type is LoadTierLayout:
            use_case = self.load_tier_layout
        if use_case_type is SaveTierLayout:
            use_case = self.save_tier_layout

        if use_case is None:
            raise TypeError(f"No provider method for {use_case_type!s} found")
        else:
            return cast(T, use_case)
