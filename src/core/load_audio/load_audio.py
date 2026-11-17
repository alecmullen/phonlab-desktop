import numpy as np
import phonlab as phon

from core.base.use_case import UseCase
from core.load_audio.entity.audio_signal import AudioSignal


class LoadAudio(UseCase[dict[int, AudioSignal]]):
    """Loads an audio file, or several files that are the channels of one recording
    (the first channel of each, in the order given, padded with silence to the length
    of the longest). Files with different sample rates cannot be channels of one
    recording: that raises ValueError."""

    def __call__(self, filename: str | list[str]):
        if isinstance(filename, str):
            *original_channels, original_fs = phon.loadsig(filename)
            signals = {}
            for idx, x in enumerate(original_channels):
                signals[idx] = AudioSignal(x, original_fs)
            yield signals
            return

        channels: list[np.ndarray] = []
        rates: set[int] = set()
        for name in filename:
            first, *_, fs = phon.loadsig(name)
            channels.append(first)
            rates.add(int(fs))
        if len(rates) > 1:
            raise ValueError(
                f"The channel files have different sample rates: {sorted(rates)}"
            )
        fs = rates.pop()
        longest = max(len(x) for x in channels)
        yield {
            idx: AudioSignal(np.pad(x, (0, longest - len(x))), fs)
            for idx, x in enumerate(channels)
        }
