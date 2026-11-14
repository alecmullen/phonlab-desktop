import numpy as np
import phonlab as phon
import pytest
from phonlab.acoustic.sgram_ import _typed_sgram

import core.spectrogram.typed_sgram as typed_sgram_module
from core.spectrogram.entity.spectrogram_type import SpectrogramType
from core.spectrogram.typed_sgram import compute_typed_sgram
from res.constants import CEPSTRAL_SEGMENT_SEC

FS = 8000
ORDER = 9


@pytest.fixture(scope="module")
def speech() -> np.ndarray:
    """A voiced-sounding signal a little longer than two cepstral segments"""
    rng = np.random.default_rng(0)
    t = np.arange(int(FS * (2 * CEPSTRAL_SEGMENT_SEC + 1.3))) / FS
    x = np.sin(2 * np.pi * (140 + 30 * np.sin(t)) * t) * (1 + np.sin(2 * np.pi * 3 * t))
    return 0.8 * x + 0.05 * rng.standard_normal(len(t))


def test_fft_is_phonlabs_compute_sgram(speech: np.ndarray):
    expected = phon.compute_sgram(speech, FS, 0.008, 0.001, ORDER)

    t, f, sxx = compute_typed_sgram(
        speech, FS, SpectrogramType.FFT, 0.008, 0.001, ORDER
    )

    np.testing.assert_array_equal(t, expected[0])
    np.testing.assert_array_equal(f, expected[1])
    np.testing.assert_array_equal(sxx, expected[2])


@pytest.mark.parametrize(
    "sgram_type", [SpectrogramType.MULTITAPER, SpectrogramType.LPC]
)
def test_other_types_give_frequency_rows_for_the_fft_size(
    speech: np.ndarray, sgram_type: SpectrogramType
):
    t, f, sxx = compute_typed_sgram(speech[:FS], FS, sgram_type, 0.025, 0.004, ORDER)

    assert len(f) == 2 ** (ORDER - 1) + 1
    assert f[-1] == pytest.approx(FS / 2)
    assert sxx.shape == (len(f), len(t))
    assert np.all(np.isfinite(sxx))


def test_cepstral_has_the_same_number_of_rows_as_the_other_types(speech: np.ndarray):
    t, f, sxx = compute_typed_sgram(
        speech[:FS], FS, SpectrogramType.CEPSTRAL, 0.04, 0.004, ORDER
    )

    assert len(f) == 2 ** (ORDER - 1) + 1
    assert f[0] == 0
    assert f[-1] == pytest.approx(FS / 2, rel=1e-3)
    assert sxx.shape == (len(f), len(t))


def test_cepstral_pieces_join_without_a_seam(speech: np.ndarray):
    """Analyzing a few seconds at a time gives what one pass over everything would"""
    t, f, sxx = compute_typed_sgram(
        speech, FS, SpectrogramType.CEPSTRAL, 0.04, 0.004, ORDER
    )

    t_whole, f_whole, sxx_whole, _, _ = _typed_sgram(
        speech, FS, "cepstral", 0.04, 0.004
    )
    rows = np.linspace(0, len(f_whole) - 1, len(f)).round().astype(int)
    np.testing.assert_allclose(t, t_whole, atol=1e-9)
    np.testing.assert_array_equal(f, f_whole[rows])
    expected = sxx_whole[rows] + 20 * np.log10(
        np.max(np.abs(speech)) / typed_sgram_module.DEFAULT_PEAK
    )
    np.testing.assert_allclose(sxx, expected, atol=1e-6)


@pytest.mark.parametrize("sgram_type", [SpectrogramType.CEPSTRAL, SpectrogramType.LPC])
def test_level_does_not_depend_on_the_loudness_of_the_audio_analyzed(
    speech: np.ndarray, sgram_type: SpectrogramType
):
    """These analyses scale their input, which would make the spectrogram of a
    window and that of the whole file differ in level. Halving the audio must
    lower the decibels by 6, as it does for the FFT"""
    loud = compute_typed_sgram(speech[:FS], FS, sgram_type, 0.03, 0.004, ORDER)[2]
    soft = compute_typed_sgram(speech[:FS] / 2, FS, sgram_type, 0.03, 0.004, ORDER)[2]

    np.testing.assert_allclose(loud - soft, 20 * np.log10(2), atol=1e-6)


def test_digital_silence_is_not_rescaled():
    sxx = np.zeros((2, 2))

    result = typed_sgram_module._restore_level(sxx, np.zeros(10))

    np.testing.assert_array_equal(result, sxx)


def test_cepstral_of_no_audio_is_an_error():
    with pytest.raises(ValueError, match="no audio"):
        compute_typed_sgram(
            np.zeros(0), FS, SpectrogramType.CEPSTRAL, 0.04, 0.004, ORDER
        )


def test_mel_rows_are_evenly_spaced_on_the_mel_scale_from_80_to_7600_hz(
    speech: np.ndarray,
):
    fs = 16000
    x = phon.prep_audio(speech[: 2 * FS], FS, target_fs=fs, preemph=0.94)[0]

    t, f, sxx = compute_typed_sgram(x, fs, SpectrogramType.MEL, 0.064, 0.004, ORDER)

    # The rows' frequencies are in mels, as phonlab gives them
    assert len(f) == 80
    assert f[0] == pytest.approx(phon.Hz_to_mel(80))
    assert f[-1] == pytest.approx(phon.Hz_to_mel(7600))
    np.testing.assert_allclose(np.diff(f), np.diff(f)[0])
    assert sxx.shape == (80, len(t))
    assert t[1] - t[0] == pytest.approx(0.004)


def test_mel_ignores_the_window_size(speech: np.ndarray):
    x = phon.prep_audio(speech[:FS], FS, target_fs=16000, preemph=0.94)[0]

    short = compute_typed_sgram(x, 16000, SpectrogramType.MEL, 0.008, 0.004, ORDER)
    long = compute_typed_sgram(x, 16000, SpectrogramType.MEL, 0.05, 0.004, ORDER)

    np.testing.assert_array_equal(short[2], long[2])
