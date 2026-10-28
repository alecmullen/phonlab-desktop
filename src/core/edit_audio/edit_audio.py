import numpy as np
from scipy.signal import resample_poly

from core.base.use_case_sync import UseCaseSync
from core.edit_audio.entity.edit_command import EditCommand, EditCommandType
from core.edit_audio.entity.edit_result import EditResult
from core.load_audio.entity.audio_signal import AudioSignal
from core.settings.app_settings import settings
from res.constants import ZERO_CROSSING_SEARCH_MS


class EditAudio(UseCaseSync[EditResult | None]):
    def _nearest_zero_crossing(self, ref_channel: AudioSignal, index: int) -> int:
        """Return the sample index within `search_radius` of `index` (inclusive)
        where the signal crosses (or touches) zero, closest to `index`. Returns
        `index` unchanged if no crossing is found"""
        if len(ref_channel.x) == 0:
            return index

        search_radius = int(ZERO_CROSSING_SEARCH_MS / 1000 * ref_channel.fs)
        clamped = min(max(index, 0), len(ref_channel.x) - 1)
        lo = max(0, clamped - search_radius)
        hi = min(len(ref_channel.x) - 1, clamped + search_radius)
        if hi <= lo:
            return index

        window = ref_channel.x[lo : hi + 1].astype(np.float64)
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
        return i0 if abs(ref_channel.x[i0]) <= abs(ref_channel.x[i1]) else i1

    def _nearest_zero_crossing_boundary(
        self, ref_channel: AudioSignal, boundary: int
    ) -> int:
        """Like `nearest_zero_crossing`, but for an EXCLUSIVE/between-samples
        position"""
        return self._nearest_zero_crossing(ref_channel, boundary - 1) + 1

    def _selected_range(
        self, ref_channel: AudioSignal, edit_command: EditCommand
    ) -> tuple[int, int] | None:
        """Validate the current selection and return it as raw-buffer
        sample indices, or emit a status message and return None."""

        fs = ref_channel.fs
        if (
            edit_command.end_time is None
            or edit_command.end_time <= edit_command.start_time
        ):
            return None
        start_idx = int(edit_command.start_time * fs)
        end_idx = int(edit_command.end_time * fs)

        if settings.cut_and_paste_at_zero_crossings:
            snapped_start = self._nearest_zero_crossing(ref_channel, start_idx)
            snapped_end = self._nearest_zero_crossing_boundary(ref_channel, end_idx)

            start_idx, end_idx = snapped_start, snapped_end

        return start_idx, end_idx

    def _resample_signal(
        self, ref_channel: AudioSignal, clip_x: np.ndarray, clip_fs: int
    ) -> np.ndarray:
        """Resample clip to the target channel fs."""
        if clip_fs == ref_channel.fs:
            return clip_x
        cd = np.gcd(clip_fs, ref_channel.fs)
        return resample_poly(
            clip_x, up=ref_channel.fs // cd, down=clip_fs // cd
        ).astype(ref_channel.x.dtype)

    def _select_clip(
        self,
        channels: dict[int, AudioSignal],
        start: int,
        end: int,
    ) -> dict[int, AudioSignal]:
        return {
            idx: AudioSignal(channel.x[start:end], channel.fs)
            for idx, channel in channels.items()
        }

    def _remove_clip(
        self, channels: dict[int, AudioSignal], start: int, end: int
    ) -> dict[int, AudioSignal]:
        return {
            idx: AudioSignal(
                np.concatenate([channel.x[:start], channel.x[end:]]), channel.fs
            )
            for idx, channel in channels.items()
        }

    def _paste_clip(
        self, clip: dict[int, AudioSignal], channels: dict[int, AudioSignal], start: int
    ) -> dict[int, AudioSignal]:
        if clip.keys() != channels.keys():
            raise ValueError("Paste not supported; channel mismatch")

        return {
            idx: AudioSignal(
                np.concatenate([channel.x[:start], clip[idx].x, channel.x[start:]]),
                channel.fs,
            )
            for idx, channel in channels.items()
        }

    def _replace_clip(
        self, channels: dict[int, AudioSignal], clip: dict[int, AudioSignal], start: int
    ) -> dict[int, AudioSignal]:
        """Overwrite samples from `start` with `clip`; channels not in `clip`
        are untouched."""
        if not clip.keys() <= channels.keys():
            raise ValueError("Replace not supported; channel mismatch")

        result = dict(channels)
        for idx, clip_channel in clip.items():
            channel = channels[idx]
            end = start + len(clip_channel.x)
            if start < 0 or end > len(channel.x):
                raise ValueError("Replace range is outside the audio")
            new_x = channel.x.copy()
            new_x[start:end] = clip_channel.x
            result[idx] = AudioSignal(new_x, channel.fs)
        return result

    def _validate_channels(
        self,
        channels: dict[int, AudioSignal],
        ref_channel: int = 0,
    ):
        for channel in channels.values():
            if len(channel.x) != len(channels[ref_channel].x):
                raise ValueError("Channel lengths don't match")
            if channel.fs != channels[ref_channel].fs:
                raise ValueError("Channel sample rates don't match")

    def __call__(
        self,
        channels: dict[int, AudioSignal],
        edit_command: EditCommand,
        ref_channel: int = 0,
    ) -> EditResult | None:

        self._validate_channels(channels, ref_channel)

        if edit_command.type == EditCommandType.COPY:
            range = self._selected_range(channels[ref_channel], edit_command)
            if range is None:
                return None
            start, end = range

            return EditResult(
                new_clip=self._select_clip(channels, start, end),
                start_idx=start,
            )

        if edit_command.type == EditCommandType.CUT:
            range = self._selected_range(channels[ref_channel], edit_command)
            if range is None:
                return None
            start, end = range

            return EditResult(
                new_audio=self._remove_clip(channels, start, end),
                new_clip=self._select_clip(channels, start, end),
                start_idx=start,
            )

        if edit_command.type == EditCommandType.PASTE:
            clip = edit_command.clip
            if clip is None:
                raise RuntimeError("Lost copied audio data")

            for idx, clip_channel in clip.items():
                if channels[ref_channel].fs != clip_channel.fs:
                    clip_x = self._resample_signal(
                        channels[ref_channel], clip_channel.x, clip_channel.fs
                    )
                    clip[idx] = AudioSignal(clip_x, channels[ref_channel].fs)

            start_idx = edit_command.start_time * channels[ref_channel].fs
            start_idx = int(np.clip(start_idx, 0, len(channels[ref_channel].x)))
            if settings.cut_and_paste_at_zero_crossings:
                start_idx = self._nearest_zero_crossing_boundary(
                    channels[ref_channel], start_idx
                )

            return EditResult(
                new_audio=self._paste_clip(clip, channels, start_idx),
                new_clip=clip,
                start_idx=start_idx,
            )

        if edit_command.type == EditCommandType.REPLACE:
            clip = edit_command.clip
            start_idx = edit_command.start_idx
            if clip is None or start_idx is None:
                raise RuntimeError("Replace needs a clip and a start index")

            new_audio = self._replace_clip(channels, clip, start_idx)
            replaced_clip = {
                idx: AudioSignal(
                    channels[idx].x[start_idx : start_idx + len(c.x)].copy(),
                    channels[idx].fs,
                )
                for idx, c in clip.items()
            }
            return EditResult(
                new_audio=new_audio,
                new_clip=clip,
                start_idx=start_idx,
                replaced_clip=replaced_clip,
            )
