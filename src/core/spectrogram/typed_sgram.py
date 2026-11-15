import numpy as np
import phonlab as phon
from phonlab.acoustic.sgram_ import _typed_sgram  # no public equivalent yet
from phonlab.utils.prep_audio_ import DEFAULT_PEAK

from core.spectrogram.entity.spectrogram_type import SpectrogramType
from res.constants import CEPSTRAL_SEGMENT_SEC


def compute_typed_sgram(
    x: np.ndarray,
    fs: int,
    sgram_type: SpectrogramType,
    window_size: float,
    step_size: float,
    order: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A spectrogram of `x` in decibels, as (times, frequencies in Hz, sxx).

    `x` must already be resampled and preemphasized (as `sgram()` would do it).
    `order` sets the FFT size, 2**order, so the number of frequency rows is the
    same whatever the type."""
    if sgram_type == SpectrogramType.FFT:
        return phon.compute_sgram(x, fs, window_size, step_size, order)
    if sgram_type == SpectrogramType.MULTITAPER:
        t, f, sxx, _, _ = _typed_sgram(
            x, fs, sgram_type, window_size, step_size, order=order
        )
        return t, f, sxx
    if sgram_type == SpectrogramType.LPC:
        # `order` is the LPC order for this type (left to be chosen automatically)
        t, f, sxx, _, _ = _typed_sgram(
            x, fs, sgram_type, window_size, step_size, nfft_order=order
        )
        return t, f, _restore_level(sxx, x)
    return _cepstral_sgram(x, fs, window_size, step_size, order)


def _cepstral_sgram(
    x: np.ndarray, fs: int, window_size: float, step_size: float, order: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The cepstrally smoothed spectrogram has a fixed 8192 frequency rows, which
    needs ~66 KB per frame: gigabytes for a long recording. So analyze a few
    seconds at a time, thin the (smooth) frequency axis to the FFT size that
    `order` asks for, and join the pieces without a seam: pieces start on the
    step grid, and each is analyzed with a window's length of audio on both sides
    so that every frame is computed from the audio around it."""
    step = max(1, round(step_size * fs))
    segment = max(1, int(CEPSTRAL_SEGMENT_SEC * fs) // step) * step
    pad = -(-int(window_size * fs) // step) * step  # a whole number of steps

    times, columns = [], []
    freqs: np.ndarray | None = None
    rows = np.empty(0, dtype=int)
    for start in range(0, len(x), segment):
        end = min(start + segment, len(x))
        first = max(start - pad, 0)
        t, f, sxx, _, _ = _typed_sgram(
            x[first : end + pad], fs, SpectrogramType.CEPSTRAL, window_size, step_size
        )
        frame = first // step + np.arange(len(t))  # index on the whole file's grid
        keep = frame >= start // step
        if end < len(x):
            keep &= frame < end // step

        if freqs is None:
            n_rows = min(2 ** (int(order) - 1) + 1, len(f))
            rows = np.linspace(0, len(f) - 1, n_rows).round().astype(int)
            freqs = f[rows]
        times.append(t[keep] + first / fs)
        columns.append(_restore_level(sxx[rows][:, keep], x[first : end + pad]))

    if freqs is None:
        raise ValueError("There is no audio to make a spectrogram of")
    return np.concatenate(times), freqs, np.hstack(columns)


def _restore_level(sxx: np.ndarray, x: np.ndarray) -> np.ndarray:
    """The cepstral and LPC analyses scale their input to a fixed peak level, so
    each call is on a level of its own: the window being looked at, and the
    whole file, would not agree. Put the decibels back on the level of `x`, the
    way the FFT and multitaper types already are."""
    peak = np.max(np.abs(x))
    if peak == 0:
        return sxx
    return sxx + 20 * np.log10(peak / DEFAULT_PEAK)
