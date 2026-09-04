import numpy as np
from scipy.signal import resample_poly

from core.base.use_case import UseCase
from core.edit_audio.entity.edit_command import EditCommand, EditCommandType
from core.edit_audio.entity.edit_result import EditResult
from core.load_audio.entity.audio_signal import AudioSignal
from core.settings.app_settings import settings
from res.constants import ZERO_CROSSING_SEARCH_MS


class EditAudio(UseCase[EditResult | None]):
    def __init__(self, channel: AudioSignal, edit_command: EditCommand):
        super().__init__()
        self._channel = channel
        self._edit_command = edit_command

        self._search_radius = int(ZERO_CROSSING_SEARCH_MS / 1000 * channel.fs)

    def _nearest_zero_crossing(self, index: int) -> int:
        """Return the sample index within `search_radius` of `index` (inclusive)
        where the signal crosses (or touches) zero, closest to `index`. Returns
        `index` unchanged if no crossing is found"""
        if len(self._channel.x) == 0:
            return index

        clamped = min(max(index, 0), len(self._channel.x) - 1)
        lo = max(0, clamped - self._search_radius)
        hi = min(len(self._channel.x) - 1, clamped + self._search_radius)
        if hi <= lo:
            return index

        window = self._channel.x[lo : hi + 1].astype(np.float64)
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
        return i0 if abs(self._channel.x[i0]) <= abs(self._channel.x[i1]) else i1

    def _nearest_zero_crossing_boundary(self, boundary: int) -> int:
        """Like `nearest_zero_crossing`, but for an EXCLUSIVE/between-samples
        position"""
        return self._nearest_zero_crossing(boundary - 1) + 1

    def _selected_range(self) -> tuple[int, int] | None:
        """Validate the current selection and return it as raw-buffer
        sample indices, or emit a status message and return None."""

        fs = self._channel.fs
        start_idx = int(self._edit_command.start_time * fs)
        end_idx = int(self._edit_command.end_time * fs)
        if end_idx <= start_idx:
            return None

        if settings.cut_and_paste_at_zero_crossings:
            snapped_start = self._nearest_zero_crossing(start_idx)
            snapped_end = self._nearest_zero_crossing_boundary(end_idx)

            if snapped_end > snapped_start:
                start_idx, end_idx = snapped_start, snapped_end

        return start_idx, end_idx

    def _resample_signal(self, clip_x: np.ndarray, clip_fs: int) -> AudioSignal:
        """Resample clip to the target channel fs."""
        if clip_fs == self._channel.fs:
            return clip_x
        cd = np.gcd(clip_fs, self._channel.fs)
        return resample_poly(
            clip_x, up=self._channel.fs // cd, down=clip_fs // cd
        ).astype(self._channel.x.dtype)

    def invoke(self):
        if self._edit_command.type == EditCommandType.COPY:
            range = self._selected_range()
            if range is None:
                return None
            start, end = range
            return EditResult(
                new_clip=AudioSignal(self._channel.x[start:end], self._channel.fs),
                start_idx=start,
            )

        if self._edit_command.type == EditCommandType.CUT:
            range = self._selected_range()
            if range is None:
                return None
            start, end = range
            new_x = np.concatenate([self._channel.x[:start], self._channel.x[end:]])
            return EditResult(
                new_channel=AudioSignal(new_x, self._channel.fs),
                new_clip=AudioSignal(self._channel.x[start:end], self._channel.fs),
                start_idx=start,
            )

        if self._edit_command.type == EditCommandType.PASTE:
            x, fs = self._edit_command.clip_x, self._edit_command.clip_fs

            if self._channel.fs != fs:
                clip_x = self._resample_signal(x, fs, self._channel.fs)
            else:
                clip_x = x

            start_idx = int(
                np.clip(self._edit_command.start_time * fs, 0, len(self._channel.x))
            )
            if settings.cut_and_paste_at_zero_crossings:
                start_idx = self._nearest_zero_crossing_boundary(start_idx)

            new_x = np.concatenate(
                [self._channel.x[:start_idx], clip_x, self._channel.x[start_idx:]]
            )
            return EditResult(new_channel=AudioSignal(new_x, self._channel.fs))

    def stop(self):
        pass
