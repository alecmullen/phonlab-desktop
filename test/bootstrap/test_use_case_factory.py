import pytest

from bootstrap.use_case_factory_impl import UseCaseFactory
from core.annotation.clear_interval import ClearInterval
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

USE_CASE_TYPES = [
    EditAudio,
    LoadAudio,
    PrepAudio,
    FilterAudio,
    SaveAudio,
    TrackFormants,
    ComputeSpectrogram,
    ComputeSpectrogramMmap,
    ClearInterval,
    CreateLabel,
    UpdateLabel,
    UpdateNode,
    DeleteNode,
    LoadAnnotation,
    ParseTextGrid,
]


@pytest.mark.parametrize("use_case_type", USE_CASE_TYPES)
def test_provide_returns_instance_of_requested_use_case(use_case_type: type):
    factory = UseCaseFactory(InMemAnnotationRepository())

    assert isinstance(factory.provide(use_case_type), use_case_type)


def test_provide_returns_same_instance_each_time():
    factory = UseCaseFactory(InMemAnnotationRepository())

    assert factory.provide(EditAudio) is factory.provide(EditAudio)


def test_provide_raises_for_unknown_use_case():
    factory = UseCaseFactory(InMemAnnotationRepository())

    with pytest.raises(TypeError):
        factory.provide(int)
