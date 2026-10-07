import numpy as np
import pytest

from core.edit_audio.filter_audio import FilterAudio, FilterSpec, FilterType

FS = 8000


def tones() -> np.ndarray:
    t = np.arange(FS) / FS
    return sum(np.sin(2 * np.pi * f * t) for f in (100, 1000, 3000))


def magnitude(y: np.ndarray, hz: int) -> float:
    return float(np.abs(np.fft.rfft(y))[hz])


def test_lowpass_removes_high_tone():
    y = FilterAudio(tones(), FS, FilterSpec(FilterType.LOWPASS, high=500)).invoke()

    assert magnitude(y, 3000) < 0.01 * magnitude(y, 100)
    assert magnitude(y, 100) > 0.9 * magnitude(tones(), 100)


def test_highpass_removes_low_tone():
    y = FilterAudio(tones(), FS, FilterSpec(FilterType.HIGHPASS, low=500)).invoke()

    assert magnitude(y, 100) < 0.01 * magnitude(y, 3000)


def test_bandpass_keeps_only_middle_tone_and_dtype():
    x = tones().astype(np.float32)
    y = FilterAudio(x, FS, FilterSpec(FilterType.BANDPASS, low=600, high=1500)).invoke()

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
