import numpy as np

from core.track_formants.entity.formant_track import FormantTrack


def make_track(*secs: float) -> FormantTrack:
    sec = np.array(secs)
    return FormantTrack(sec, np.repeat(sec[:, None], 4, axis=1) * 1000)


def test_default_track_is_empty():
    track = FormantTrack()

    assert len(track.sec) == 0
    assert track.formants.shape == (0, 4)


def test_merged_with_interleaves_frames_in_time_order():
    merged = make_track(0.03, 0.04).merged_with(make_track(0.01, 0.02))

    np.testing.assert_array_equal(merged.sec, [0.01, 0.02, 0.03, 0.04])
    np.testing.assert_array_equal(merged.formants[:, 0], [10, 20, 30, 40])


def test_merged_with_empty_track_is_unchanged():
    merged = FormantTrack().merged_with(make_track(0.01))

    np.testing.assert_array_equal(merged.sec, [0.01])
    assert merged.formants.shape == (1, 4)


def test_between_includes_both_ends():
    track = make_track(0.01, 0.02, 0.03, 0.04, 0.05)

    window = track.between(0.02, 0.04)

    np.testing.assert_array_equal(window.sec, [0.02, 0.03, 0.04])
    np.testing.assert_array_equal(window.formants[:, 0], [20, 30, 40])


def test_between_outside_the_track_is_empty():
    assert len(make_track(0.01, 0.02).between(5.0, 6.0).sec) == 0
