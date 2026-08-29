import numpy as np
import soundfile as sf

import phonlab as phon


def save_audio_signal(raw_x: np.ndarray, raw_fs: int, path: str, target_fs: int, scale: bool):
    """Write raw (native-amplitude) audio to `path`, resampled to
    target_fs and optionally scaled. No preemphasis or dither — those are
    analysis-buffer conveniences, not things to permanently bake into a
    saved file."""
    x, fs = phon.prep_audio(
        raw_x, raw_fs, target_fs=target_fs, scale=scale, pre=0, add_tiny_noise=False
    )
    sf.write(path, x, fs, subtype="PCM_16")
