import numpy as np
from scipy.signal import resample_poly

from core.base.use_case_sync import UseCaseSync
from core.edit_audio.entity.edit_command import EditCommand, EditCommandType
from core.edit_audio.entity.edit_result import EditResult
from core.load_audio.entity.audio_signal import AudioSignal
from core.settings.app_settings import settings
from res.constants import ZERO_CROSSING_SEARCH_MS


class EditAudio(UseCaseSync[EditResult | None]):
    def __init__(
        self,
        channels: dict[int, AudioSignal],
        edit_command: EditCommand,
        ref_channel: int = 0,
    ):
        super().__init__()
        self._edit_command = edit_command

        self._ref_channel = channels[ref_channel]
        self._channels: dict[int, AudioSignal] = {}

        for idx, channel in channels.items():
            if len(channel.x) != len(self._ref_channel.x):
                raise ValueError("Channel lengths don't match")
            if channel.fs != self._ref_channel.fs:
                raise ValueError("Channel sample rates don't match")

            self._channels[idx] = channel

        self._search_radius = int(ZERO_CROSSING_SEARCH_MS / 1000 * self._ref_channel.fs)

    def _nearest_zero_crossing(self, index: int) -> int:
        """Return the sample index within `search_radius` of `index` (inclusive)
        where the signal crosses (or touches) zero, closest to `index`. Returns
        `index` unchanged if no crossing is found"""
        if len(self._ref_channel.x) == 0:
            return index

        clamped = min(max(index, 0), len(self._ref_channel.x) - 1)
        lo = max(0, clamped - self._search_radius)
        hi = min(len(self._ref_channel.x) - 1, clamped + self._search_radius)
        if hi <= lo:
            return index

        window = self._ref_channel.x[lo : hi + 1].astype(np.float64)
        signs = np.sign(window)
        signs[signs == 0] = 1
        crossing_offsets = np.where(np.diff(signs) != 0)[0]
        if len(crossing_offsets) == 0:
            return index  # no crossing nearby; leave the original position untouched

        target_offset = clamped - lo
        best_offset = crossing_offsets[
            np.argmin(np.abs(crossing_offsets - target_offset))
        ]
        i0, i1 = lo + best_offset, lo + best_offset + 1
        return (
            i0 if abs(self._ref_channel.x[i0]) <= abs(self._ref_channel.x[i1]) else i1
        )

    def _nearest_zero_crossing_boundary(self, boundary: int) -> int:
        """Like `nearest_zero_crossing`, but for an EXCLUSIVE/between-samples
        position"""
        return self._nearest_zero_crossing(boundary - 1) + 1

    def _selected_range(self) -> tuple[int, int] | None:
        """Validate the current selection and return it as raw-buffer
        sample indices, or emit a status message and return None."""

        fs = self._ref_channel.fs
        if (
            self._edit_command.end_time is None
            or self._edit_command.end_time <= self._edit_command.start_time
        ):
            return None
        start_idx = int(self._edit_command.start_time * fs)
        end_idx = int(self._edit_command.end_time * fs)

        if settings.cut_and_paste_at_zero_crossings:
            snapped_start = self._nearest_zero_crossing(start_idx)
            snapped_end = self._nearest_zero_crossing_boundary(end_idx)

            start_idx, end_idx = snapped_start, snapped_end

        return start_idx, end_idx

    def _resample_signal(self, clip_x: np.ndarray, clip_fs: int) -> np.ndarray:
        """Resample clip to the target channel fs."""
        if clip_fs == self._ref_channel.fs:
            return clip_x
        cd = np.gcd(clip_fs, self._ref_channel.fs)
        return resample_poly(
            clip_x, up=self._ref_channel.fs // cd, down=clip_fs // cd
        ).astype(self._ref_channel.x.dtype)

    def _select_clip(self, start: int, end: int) -> dict[int, AudioSignal]:
        return {
            idx: AudioSignal(channel.x[start:end], channel.fs)
            for idx, channel in self._channels.items()
        }

    def _remove_clip(self, start: int, end: int) -> dict[int, AudioSignal]:
        return {
            idx: AudioSignal(
                np.concatenate([channel.x[:start], channel.x[end:]]), channel.fs
            )
            for idx, channel in self._channels.items()
        }

    def _paste_clip(
        self, clip: dict[int, AudioSignal], start: int
    ) -> dict[int, AudioSignal]:
        if clip.keys() != self._channels.keys():
            raise ValueError("Paste not supported; channel mismatch")

        return {
            idx: AudioSignal(
                np.concatenate([channel.x[:start], clip[idx].x, channel.x[start:]]),
                channel.fs,
            )
            for idx, channel in self._channels.items()
        }

    def invoke(self) -> EditResult | None:
        if self._edit_command.type == EditCommandType.COPY:
            range = self._selected_range()
            if range is None:
                return None
            start, end = range

            return EditResult(
                new_clip=self._select_clip(start, end),
                start_idx=start,
            )

        if self._edit_command.type == EditCommandType.CUT:
            range = self._selected_range()
            if range is None:
                return None
            start, end = range

            return EditResult(
                new_audio=self._remove_clip(start, end),
                new_clip=self._select_clip(start, end),
                start_idx=start,
            )

        if self._edit_command.type == EditCommandType.PASTE:
            clip = self._edit_command.clip
            if clip is None:
                raise RuntimeError("Lost copied audio data")

            for idx, clip_channel in clip.items():
                if self._ref_channel.fs != clip_channel.fs:
                    clip_x = self._resample_signal(clip_channel.x, clip_channel.fs)
                    clip[idx] = AudioSignal(clip_x, self._ref_channel.fs)

            start_idx = self._edit_command.start_time * self._ref_channel.fs
            start_idx = int(np.clip(start_idx, 0, len(self._ref_channel.x)))
            if settings.cut_and_paste_at_zero_crossings:
                start_idx = self._nearest_zero_crossing_boundary(start_idx)

            return EditResult(
                new_audio=self._paste_clip(clip, start_idx),
                new_clip=clip,
                start_idx=start_idx,
            )
