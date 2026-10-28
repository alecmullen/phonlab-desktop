from typing import Any, cast

from core.annotation.create_label import CreateLabel
from core.annotation.delete_node import DeleteNode
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
from ui.spectrogram.spectrogram_view_model import SpectrogramViewModel
from ui.waveform.audio_wave_view_model import AudioWaveViewModel


class ViewModelFactoryImpl(ViewModelFactory):
    def __init__(self):
        self.edit_audio = EditAudio()
        self.load_audio = LoadAudio()
        self.prep_audio = PrepAudio()
        self.filter_audio = FilterAudio()
        self.save_audio = SaveAudio()
        self.track_formants = TrackFormants()
        self.compute_sgram = ComputeSpectrogram()
        self.compute_sgram_mmap = ComputeSpectrogramMmap()
        self.create_label = CreateLabel()
        self.delete_node = DeleteNode()
        self.parse_textgrid = ParseTextGrid()

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

        if view_model is None:
            raise TypeError(f"No provider method for {view_model_type!s} found")
        else:
            return cast(T, view_model)

    def create_document_view_model(self) -> DocumentViewModel:
        return DocumentViewModel(
            self,
            self.edit_audio,
            self.load_audio,
            self.prep_audio,
            self.filter_audio,
            self.save_audio,
        )

    def create_spectrogram_view_model(self) -> SpectrogramViewModel:
        return SpectrogramViewModel(
            self.track_formants,
            self.prep_audio,
            self.compute_sgram,
            self.compute_sgram_mmap,
        )

    def create_annotation_view_model(self) -> AnnotationViewModel:
        return AnnotationViewModel(
            self.create_label, self.delete_node, self.parse_textgrid
        )

    def create_audio_wave_view_model(self, channel_idx: int) -> AudioWaveViewModel:
        return AudioWaveViewModel(channel_idx)
