from collections.abc import Callable
from functools import partial

import numpy as np
import pytest

from core.edit_audio.edit_audio import EditAudio
from core.edit_audio.entity.edit_command import EditCommand, EditCommandType
from core.load_audio.entity.audio_signal import AudioSignal
from core.settings.app_settings import settings


def make_channel(x: list[float], fs: int = 1000) -> AudioSignal:
    return AudioSignal(np.array(x, dtype=np.float64), fs)


def make_edit(channel: AudioSignal, **command_kwargs: object) -> Callable:
    """An `EditAudio` call on a single channel, ready to be invoked"""
    command_kwargs.setdefault("type", EditCommandType.COPY)
    command_kwargs.setdefault("start_time", 0.0)
    return partial(EditAudio(), {0: channel}, EditCommand(**command_kwargs))


def selected_range(
    channel: AudioSignal, **command_kwargs: object
) -> tuple[int, int] | None:
    command_kwargs.setdefault("type", EditCommandType.COPY)
    command_kwargs.setdefault("start_time", 0.0)
    return EditAudio()._selected_range(channel, EditCommand(**command_kwargs))


# --------------------------- _nearest_zero_crossing ---------------------------


def test_nearest_zero_crossing_returns_index_unchanged_for_empty_channel():
    channel = make_channel([])

    assert EditAudio()._nearest_zero_crossing(channel, 5) == 5


def test_nearest_zero_crossing_returns_index_unchanged_when_no_crossing_found():
    channel = make_channel([1, 1, 1, 1, 1])

    assert EditAudio()._nearest_zero_crossing(channel, 2) == 2


def test_nearest_zero_crossing_finds_nearby_crossing():
    channel = make_channel([1, 1, 1, -1, -1])

    assert EditAudio()._nearest_zero_crossing(channel, 0) == 2


def test_nearest_zero_crossing_prefers_smaller_magnitude_sample_after_crossing():
    channel = make_channel([3, -1])

    assert EditAudio()._nearest_zero_crossing(channel, 0) == 1


def test_nearest_zero_crossing_prefers_smaller_magnitude_sample_before_crossing():
    channel = make_channel([1, -3])

    assert EditAudio()._nearest_zero_crossing(channel, 0) == 0


def test_nearest_zero_crossing_treats_zero_as_positive():
    channel = make_channel([1, 0, -1])

    assert EditAudio()._nearest_zero_crossing(channel, 1) == 1


def test_nearest_zero_crossing_respects_search_radius():
    x = [1.0] * 20 + [-1.0] * 20
    channel = make_channel(x)

    # search_radius is 5 samples (5ms @ 1000Hz); the crossing at 19/20 is
    # far outside the window around index 0.
    assert EditAudio()._nearest_zero_crossing(channel, 0) == 0


def test_nearest_zero_crossing_finds_crossing_within_radius():
    x = [1.0] * 20 + [-1.0] * 20
    channel = make_channel(x)

    assert EditAudio()._nearest_zero_crossing(channel, 17) == 19


def test_nearest_zero_crossing_boundary_is_one_past_preceding_crossing():
    channel = make_channel([1, 1, 1, -1, -1])

    assert EditAudio()._nearest_zero_crossing_boundary(channel, 1) == 3


# --------------------------- _selected_range ---------------------------


def test_selected_range_returns_none_when_end_time_missing():
    assert (
        selected_range(make_channel([0] * 100), start_time=0.01, end_time=None) is None
    )


def test_selected_range_returns_none_when_end_not_after_start():
    assert (
        selected_range(make_channel([0] * 100), start_time=0.02, end_time=0.02) is None
    )


def test_selected_range_converts_times_to_sample_indices_without_snapping(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    assert selected_range(make_channel([0] * 100), start_time=0.01, end_time=0.02) == (
        10,
        20,
    )


def test_selected_range_snaps_to_nearby_zero_crossings_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", True)
    x = [1.0] * 9 + [-1.0] * 9 + [1.0] * 9 + [-1.0] * 9
    assert selected_range(make_channel(x), start_time=0.01, end_time=0.02) == (8, 18)


def test_selected_range_keeps_raw_indices_when_no_crossings_nearby(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", True)
    assert selected_range(
        make_channel([1.0] * 100), start_time=0.01, end_time=0.02
    ) == (10, 20)


def test_selected_range_does_not_collapse_when_only_one_zero_crossing(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", True)
    start, end = selected_range(
        make_channel([1.0, 1.0, -0.5, -1.0]), start_time=0.0, end_time=0.004
    )

    assert start != end


# --------------------------- invoke: COPY ---------------------------


def test_copy_returns_none_when_no_valid_selection(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    edit = make_edit(
        make_channel(list(range(10))),
        type=EditCommandType.COPY,
        start_time=0.01,
        end_time=None,
    )

    assert edit() is None


def test_copy_returns_clip_without_modifying_channel(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    channel = make_channel(list(range(10)))
    edit = make_edit(
        channel, type=EditCommandType.COPY, start_time=0.002, end_time=0.005
    )

    result = edit()

    np.testing.assert_array_equal(result.new_clip[0].x, [2, 3, 4])
    assert result.start_idx == 2
    np.testing.assert_array_equal(channel.x, list(range(10)))


# --------------------------- invoke: CUT ---------------------------


def test_cut_returns_none_when_no_valid_selection(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    edit = make_edit(
        make_channel(list(range(10))),
        type=EditCommandType.CUT,
        start_time=0.005,
        end_time=0.001,
    )

    assert edit() is None


def test_cut_removes_selected_range_and_returns_clip(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    edit = make_edit(
        make_channel(list(range(10))),
        type=EditCommandType.CUT,
        start_time=0.002,
        end_time=0.005,
    )

    result = edit()

    np.testing.assert_array_equal(result.new_clip[0].x, [2, 3, 4])
    np.testing.assert_array_equal(result.new_audio[0].x, [0, 1, 5, 6, 7, 8, 9])
    assert result.start_idx == 2


# --------------------------- invoke: PASTE ---------------------------


def test_paste_raises_when_clip_data_missing():
    edit = make_edit(
        make_channel(list(range(10))), type=EditCommandType.PASTE, start_time=0.0
    )

    with pytest.raises(RuntimeError):
        edit()


def test_paste_inserts_clip_at_start_index(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    edit = make_edit(
        make_channel([0] * 10),
        type=EditCommandType.PASTE,
        start_time=0.003,
        clip={0: make_channel(np.array([9.0, 9.0]), 1000)},
    )

    result = edit()

    np.testing.assert_array_equal(
        result.new_audio[0].x, [0, 0, 0, 9, 9, 0, 0, 0, 0, 0, 0, 0]
    )
    assert result.start_idx == 3


def test_paste_resamples_clip_when_fs_differs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    edit = make_edit(
        make_channel([0.0] * 10, fs=8000),
        type=EditCommandType.PASTE,
        start_time=0.0,
        clip={0: make_channel(np.zeros(50, dtype=np.float64), 4000)},
    )

    result = edit()

    assert len(result.new_audio[0].x) == 10 + 100


def test_paste_clamps_start_index_above_channel_length(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    channel = make_channel(list(range(10)))
    edit = make_edit(
        channel,
        type=EditCommandType.PASTE,
        start_time=100.0,
        clip={0: make_channel(np.array([9.0]), 1000)},
    )

    result = edit()

    np.testing.assert_array_equal(
        result.new_audio[0].x, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9]
    )
    assert result.start_idx == 10


def test_paste_clamps_start_index_below_zero(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)
    edit = make_edit(
        make_channel(list(range(10))),
        type=EditCommandType.PASTE,
        start_time=-5.0,
        clip={0: make_channel(np.array([9.0]), 1000)},
    )

    result = edit()

    np.testing.assert_array_equal(
        result.new_audio[0].x, [9, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    )
    assert result.start_idx == 0


def test_paste_snaps_insertion_point_to_zero_crossing_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", True)
    x = [1.0] * 9 + [-1.0] * 9 + [1.0] * 9 + [-1.0] * 9
    edit = make_edit(
        make_channel(x),
        type=EditCommandType.PASTE,
        start_time=0.02,
        clip={0: make_channel(np.array([5.0, 5.0]), 1000)},
    )

    result = edit()

    assert result.start_idx == 18
    np.testing.assert_array_equal(result.new_audio[0].x[18:20], [5.0, 5.0])


# --------------------------------- REPLACE ---------------------------------


def make_replace(
    channels: dict[int, AudioSignal], clip: dict[int, AudioSignal], start: int
) -> Callable:
    return partial(
        EditAudio(),
        channels,
        EditCommand(EditCommandType.REPLACE, 0.0, clip=clip, start_idx=start),
        ref_channel=next(iter(channels)),
    )


def test_replace_overwrites_samples_and_reports_previous():
    channel = make_channel([1, 2, 3, 4, 5])

    result = make_replace({0: channel}, {0: make_channel([9, 8])}, 1)()

    np.testing.assert_array_equal(result.new_audio[0].x, [1, 9, 8, 4, 5])
    np.testing.assert_array_equal(result.new_clip[0].x, [9, 8])
    np.testing.assert_array_equal(result.replaced_clip[0].x, [2, 3])
    assert result.start_idx == 1


def test_replace_does_not_mutate_input():
    channel = make_channel([1, 2, 3])

    make_replace({0: channel}, {0: make_channel([0, 0])}, 0)()

    np.testing.assert_array_equal(channel.x, [1, 2, 3])


def test_replace_leaves_channels_outside_clip_untouched():
    left, right = make_channel([1, 2, 3]), make_channel([4, 5, 6])

    result = make_replace({0: left, 1: right}, {1: make_channel([0, 0])}, 1)()

    np.testing.assert_array_equal(result.new_audio[0].x, [1, 2, 3])
    np.testing.assert_array_equal(result.new_audio[1].x, [4, 0, 0])


def test_replace_ignores_zero_crossing_snapping(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", True)
    channel = make_channel([1, 1, -1, -1, 1])

    result = make_replace({0: channel}, {0: make_channel([7])}, 1)()

    assert result.start_idx == 1
    np.testing.assert_array_equal(result.new_audio[0].x, [1, 7, -1, -1, 1])


def test_replace_past_end_raises():
    with pytest.raises(ValueError):
        make_replace({0: make_channel([1, 2])}, {0: make_channel([1, 2])}, 1)()


def test_replace_unknown_channel_raises():
    with pytest.raises(ValueError):
        make_replace({0: make_channel([1, 2])}, {1: make_channel([1])}, 0)()


def test_replace_needs_clip_and_start_index():
    edit = make_edit(make_channel([1, 2]), type=EditCommandType.REPLACE)

    with pytest.raises(RuntimeError):
        edit()
