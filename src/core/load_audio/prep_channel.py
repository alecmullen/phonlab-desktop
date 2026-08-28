import numpy as np
import phonlab as phon

from core.load_audio.entity.audio_signal import AudioSignal


def prep_channel(raw: np.ndarray, fs: int, target_fs: int) -> AudioSignal:
    """Prepare one raw channel for analysis/display, using the same params
    everywhere a document's analysis buffer is (re)derived from its raw
    audio: at file load, when a clip tab is created from copied/cut
    samples, and whenever cut/paste/undo/redo replaces the raw buffer."""
    x, prepped_fs = phon.prep_audio(
        raw, fs, target_fs=target_fs, scale=True, pre=0.94, add_tiny_noise=True
    )
    return AudioSignal(x, prepped_fs)
