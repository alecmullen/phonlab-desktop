import numpy as np
import pytest

from core.edit_audio.edit_audio import EditAudio
from core.edit_audio.entity.edit_command import EditCommand, EditCommandType
from core.load_audio.entity.audio_signal import AudioSignal
from core.settings.app_settings import settings


def make_channel(x: list[float], fs: int = 1000) -> AudioSignal:
    return AudioSignal(np.array(x, dtype=np.float64), fs)


def make_use_case(channel: AudioSignal, **command_kwargs: object) -> EditAudio:
    command_kwargs.setdefault("type", EditCommandType.COPY)
    command_kwargs.setdefault("start_time", 0.0)
    return EditAudio(channel, EditCommand(**command_kwargs))


# --------------------------- _nearest_zero_crossing ---------------------------


def test_nearest_zero_crossing_returns_index_unchanged_for_empty_channel():
    use_case = make_use_case(make_channel([]))

    assert use_case._nearest_zero_crossing(5) == 5


def test_nearest_zero_crossing_returns_index_unchanged_when_no_crossing_found():
    use_case = make_use_case(make_channel([1, 1, 1, 1, 1]))

    assert use_case._nearest_zero_crossing(2) == 2


def test_nearest_zero_crossing_finds_nearby_crossing():
    use_case = make_use_case(make_channel([1, 1, 1, -1, -1]))

    assert use_case._nearest_zero_crossing(0) == 2


def test_nearest_zero_crossing_prefers_smaller_magnitude_sample_after_crossing():
    use_case = make_use_case(make_channel([3, -1]))

    assert use_case._nearest_zero_crossing(0) == 1


def test_nearest_zero_crossing_prefers_smaller_magnitude_sample_before_crossing():
    use_case = make_use_case(make_channel([1, -3]))

    assert use_case._nearest_zero_crossing(0) == 0


def test_nearest_zero_crossing_treats_zero_as_positive():
    use_case = make_use_case(make_channel([1, 0, -1]))

    assert use_case._nearest_zero_crossing(1) == 1


def test_nearest_zero_crossing_respects_search_radius():
    x = [1.0] * 20 + [-1.0] * 20
    use_case = make_use_case(make_channel(x))

    # search_radius is 5 samples (5ms @ 1000Hz); the crossing at 19/20 is
    # far outside the window around index 0.
    assert use_case._nearest_zero_crossing(0) == 0


def test_nearest_zero_crossing_finds_crossing_within_radius():
    x = [1.0] * 20 + [-1.0] * 20
    use_case = make_use_case(make_channel(x))

    assert use_case._nearest_zero_crossing(17) == 19


def test_nearest_zero_crossing_boundary_is_one_past_preceding_crossing():
    use_case = make_use_case(make_channel([1, 1, 1, -1, -1]))

    assert use_case._nearest_zero_crossing_boundary(1) == 3


# --------------------------- _selected_range ---------------------------


def test_selected_range_returns_none_when_end_time_missing():
    use_case = make_use_case(make_channel([0] * 100), start_time=0.01, end_time=None)

    assert use_case._selected_range() is None


def test_selected_range_returns_none_when_end_not_after_start():
    use_case = make_use_case(make_channel([0] * 100), start_time=0.02, end_time=0.02)

    assert use_case._selected_range() is None


def test_selected_range_converts_times_to_sample_indices_without_snapping(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    use_case = make_use_case(make_channel([0] * 100), start_time=0.01, end_time=0.02)

    assert use_case._selected_range() == (10, 20)


def test_selected_range_snaps_to_nearby_zero_crossings_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", True)
    x = [1.0] * 9 + [-1.0] * 9 + [1.0] * 9 + [-1.0] * 9
    use_case = make_use_case(make_channel(x), start_time=0.01, end_time=0.02)

    assert use_case._selected_range() == (8, 18)


def test_selected_range_keeps_raw_indices_when_no_crossings_nearby(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", True)
    use_case = make_use_case(make_channel([1.0] * 100), start_time=0.01, end_time=0.02)

    assert use_case._selected_range() == (10, 20)


def test_selected_range_does_not_collapse_when_only_one_zero_crossing(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", True)
    use_case = make_use_case(
        make_channel([1.0, 1.0, -0.5, -1.0]), start_time=0.0, end_time=0.004
    )

    selected_range = use_case._selected_range()
    assert selected_range[0] != selected_range[1]


# --------------------------- _resample_signal ---------------------------


def test_resample_signal_returns_clip_unchanged_when_fs_matches():
    use_case = make_use_case(make_channel([0] * 10, fs=8000))
    clip = np.zeros(50, dtype=np.float64)

    result = use_case._resample_signal(clip, 8000)

    assert result is clip


def test_resample_signal_resamples_to_target_length():
    use_case = make_use_case(make_channel([0] * 10, fs=8000))
    clip = np.zeros(100, dtype=np.float64)

    result = use_case._resample_signal(clip, 4000)

    assert len(result) == 200
    assert result.dtype == use_case._channel.x.dtype


# --------------------------- invoke: COPY ---------------------------


def test_copy_returns_none_when_no_valid_selection(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    use_case = make_use_case(
        make_channel(list(range(10))),
        type=EditCommandType.COPY,
        start_time=0.01,
        end_time=None,
    )

    assert use_case.invoke() is None


def test_copy_returns_clip_without_modifying_channel(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    channel = make_channel(list(range(10)))
    use_case = make_use_case(
        channel, type=EditCommandType.COPY, start_time=0.002, end_time=0.005
    )

    result = use_case.invoke()

    np.testing.assert_array_equal(result.new_clip.x, [2, 3, 4])
    assert result.start_idx == 2
    np.testing.assert_array_equal(channel.x, list(range(10)))


# --------------------------- invoke: CUT ---------------------------


def test_cut_returns_none_when_no_valid_selection(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    use_case = make_use_case(
        make_channel(list(range(10))),
        type=EditCommandType.CUT,
        start_time=0.005,
        end_time=0.001,
    )

    assert use_case.invoke() is None


def test_cut_removes_selected_range_and_returns_clip(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    use_case = make_use_case(
        make_channel(list(range(10))),
        type=EditCommandType.CUT,
        start_time=0.002,
        end_time=0.005,
    )

    result = use_case.invoke()

    np.testing.assert_array_equal(result.new_clip.x, [2, 3, 4])
    np.testing.assert_array_equal(result.new_channel.x, [0, 1, 5, 6, 7, 8, 9])
    assert result.start_idx == 2


# --------------------------- invoke: PASTE ---------------------------


def test_paste_raises_when_clip_data_missing():
    use_case = make_use_case(
        make_channel(list(range(10))), type=EditCommandType.PASTE, start_time=0.0
    )

    with pytest.raises(RuntimeError):
        use_case.invoke()


def test_paste_inserts_clip_at_start_index(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    use_case = make_use_case(
        make_channel([0] * 10),
        type=EditCommandType.PASTE,
        start_time=0.003,
        clip_x=np.array([9.0, 9.0]),
        clip_fs=1000,
    )

    result = use_case.invoke()

    np.testing.assert_array_equal(
        result.new_channel.x, [0, 0, 0, 9, 9, 0, 0, 0, 0, 0, 0, 0]
    )
    assert result.start_idx == 3


def test_paste_resamples_clip_when_fs_differs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    use_case = make_use_case(
        make_channel([0.0] * 10, fs=8000),
        type=EditCommandType.PASTE,
        start_time=0.0,
        clip_x=np.zeros(50, dtype=np.float64),
        clip_fs=4000,
    )

    result = use_case.invoke()

    assert len(result.new_channel.x) == 10 + 100


def test_paste_clamps_start_index_above_channel_length(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    channel = make_channel(list(range(10)))
    use_case = make_use_case(
        channel,
        type=EditCommandType.PASTE,
        start_time=100.0,
        clip_x=np.array([9.0]),
        clip_fs=1000,
    )

    result = use_case.invoke()

    np.testing.assert_array_equal(
        result.new_channel.x, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9]
    )
    assert result.start_idx == 10


def test_paste_clamps_start_index_below_zero(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    use_case = make_use_case(
        make_channel(list(range(10))),
        type=EditCommandType.PASTE,
        start_time=-5.0,
        clip_x=np.array([9.0]),
        clip_fs=1000,
    )

    result = use_case.invoke()

    np.testing.assert_array_equal(
        result.new_channel.x, [9, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    )
    assert result.start_idx == 0


def test_paste_snaps_insertion_point_to_zero_crossing_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", True)
    x = [1.0] * 9 + [-1.0] * 9 + [1.0] * 9 + [-1.0] * 9
    use_case = make_use_case(
        make_channel(x),
        type=EditCommandType.PASTE,
        start_time=0.02,
        clip_x=np.array([5.0, 5.0]),
        clip_fs=1000,
    )

    result = use_case.invoke()

    assert result.start_idx == 18
    np.testing.assert_array_equal(result.new_channel.x[18:20], [5.0, 5.0])
