import numpy as np

from core.edit_audio.transform_audio import ReverseAudio, ScaleAudio


def test_scale_audio_sets_peak_to_requested_dbfs():
    x = np.array([0.1, -0.2, 0.05], dtype=np.float64)

    y = ScaleAudio(x, 16000, 0).invoke()

    assert np.max(np.abs(y)) == np.float64(1.0)
    assert len(y) == len(x)


def test_scale_audio_negative_dbfs_and_dtype_preserved():
    x = np.array([0.5, -0.25], dtype=np.float32)

    y = ScaleAudio(x, 16000, -6).invoke()

    assert y.dtype == np.float32
    assert np.isclose(np.max(np.abs(y)), 10 ** (-6 / 20), rtol=1e-5)


def test_scale_audio_silence_is_left_alone():
    y = ScaleAudio(np.zeros(10), 16000, -1).invoke()

    np.testing.assert_array_equal(y, np.zeros(10))


def test_reverse_audio_reverses_and_does_not_alias_input():
    x = np.arange(5)

    y = ReverseAudio(x).invoke()

    np.testing.assert_array_equal(y, [4, 3, 2, 1, 0])
    y[0] = 99
    np.testing.assert_array_equal(x, np.arange(5))
