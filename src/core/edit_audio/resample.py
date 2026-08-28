import numpy as np
from scipy.signal import resample_poly


def resample_signal(x: np.ndarray, fs: int, target_fs: int) -> np.ndarray:
    """Resample x from fs to target_fs with no other processing (no polarity
    flip, scaling, or dither, unlike phon.prep_audio)."""
    if fs == target_fs:
        return x
    cd = np.gcd(fs, target_fs)
    return resample_poly(x, up=target_fs // cd, down=fs // cd).astype(x.dtype)
