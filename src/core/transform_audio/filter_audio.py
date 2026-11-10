from scipy.signal import butter, sosfiltfilt

from core.base.use_case_sync import UseCaseSync
from core.load_audio.entity.audio_signal import AudioSignal
from core.transform_audio.entity.filter_spec import FilterSpec


class FilterAudio(UseCaseSync[dict[int, AudioSignal]]):
    """Zero-phase Butterworth filter (forward-backward second-order sections)
    applied to each channel."""

    def __call__(
        self, channels: dict[int, AudioSignal], spec: FilterSpec
    ) -> dict[int, AudioSignal]:
        filtered = {}
        for idx, channel in channels.items():
            sos = butter(
                spec.order,
                spec.bounds(),
                fs=channel.fs,
                btype=str(spec.type),
                output="sos",
            )
            x = sosfiltfilt(sos, channel.x).astype(channel.x.dtype, copy=False)
            filtered[idx] = AudioSignal(x, channel.fs)
        return filtered
