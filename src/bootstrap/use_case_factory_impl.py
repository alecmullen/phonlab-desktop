from typing import cast

from core.annotation.clear_interval import ClearInterval
from core.annotation.create_label import CreateLabel
from core.annotation.delete_node import DeleteNode
from core.annotation.load_annotation import LoadAnnotation
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.annotation.update_label import UpdateLabel
from core.annotation.update_node import UpdateNode
from core.edit_audio.edit_audio import EditAudio
from core.load_audio.load_audio import LoadAudio
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.parse_textgrid.write_textgrid import WriteTextGrid
from core.save_audio.save_audio import SaveAudio
from core.spectrogram.compute_sgram import ComputeSpectrogram
from core.spectrogram.compute_sgram_mmap import ComputeSpectrogramMmap
from core.track_formants.track_formants import TrackFormants
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
        self.compute_sgram = ComputeSpectrogram()
        self.compute_sgram_mmap = ComputeSpectrogramMmap()
        self.clear_interval = ClearInterval(self.annotation_repository)
        self.create_label = CreateLabel(self.clear_interval, self.annotation_repository)
        self.update_label = UpdateLabel(self.annotation_repository)
        self.update_node = UpdateNode(self.annotation_repository)
        self.delete_node = DeleteNode(self.annotation_repository)
        self.load_annotation = LoadAnnotation(self.annotation_repository)
        self.parse_textgrid = ParseTextGrid(self.annotation_repository)
        self.write_textgrid = WriteTextGrid()

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
        if use_case_type is UpdateNode:
            use_case = self.update_node
        if use_case_type is DeleteNode:
            use_case = self.delete_node
        if use_case_type is LoadAnnotation:
            use_case = self.load_annotation
        if use_case_type is ParseTextGrid:
            use_case = self.parse_textgrid
        if use_case_type is WriteTextGrid:
            use_case = self.write_textgrid

        if use_case is None:
            raise TypeError(f"No provider method for {use_case_type!s} found")
        else:
            return cast(T, use_case)
