import numpy as np
import pytest

from core.load_audio.entity.audio_signal import AudioSignal
from core.transform_audio.entity.filter_spec import FilterType
from core.transform_audio.filter_audio import FilterAudio, FilterSpec

FS = 8000


def tones() -> np.ndarray:
    t = np.arange(FS) / FS
    return sum(np.sin(2 * np.pi * f * t) for f in (100, 1000, 3000))


def run_filter(x: np.ndarray, spec: FilterSpec) -> np.ndarray:
    return FilterAudio({0: AudioSignal(x, FS)}, spec).invoke()[0].x


def magnitude(y: np.ndarray, hz: int) -> float:
    return float(np.abs(np.fft.rfft(y))[hz])


def test_lowpass_removes_high_tone():
    y = run_filter(tones(), FilterSpec(FilterType.LOWPASS, high=500))

    assert magnitude(y, 3000) < 0.01 * magnitude(y, 100)
    assert magnitude(y, 100) > 0.9 * magnitude(tones(), 100)


def test_highpass_removes_low_tone():
    y = run_filter(tones(), FilterSpec(FilterType.HIGHPASS, low=500))

    assert magnitude(y, 100) < 0.01 * magnitude(y, 3000)


def test_bandpass_keeps_only_middle_tone_and_dtype():
    x = tones().astype(np.float32)
    y = run_filter(x, FilterSpec(FilterType.BANDPASS, low=600, high=1500))

    assert y.dtype == np.float32
    assert magnitude(y, 100) < 0.01 * magnitude(y, 1000)
    assert magnitude(y, 3000) < 0.01 * magnitude(y, 1000)


def test_missing_edges_raise():
    with pytest.raises(ValueError):
        FilterSpec(FilterType.BANDPASS, low=100).bounds()
    with pytest.raises(ValueError):
        FilterSpec(FilterType.LOWPASS).bounds()
    with pytest.raises(ValueError):
        FilterSpec(FilterType.HIGHPASS).bounds()


def test_filters_every_channel_at_its_own_sample_rate():
    channels = {
        0: AudioSignal(tones(), FS),
        1: AudioSignal(tones()[:4000], FS),
    }

    result = FilterAudio(channels, FilterSpec(FilterType.LOWPASS, high=500)).invoke()

    assert result.keys() == channels.keys()
    assert len(result[1].x) == 4000
    assert result[0].fs == FS
    assert magnitude(result[0].x, 3000) < 0.01 * magnitude(result[0].x, 100)
