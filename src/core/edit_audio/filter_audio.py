from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from scipy.signal import butter, sosfiltfilt

from core.base.use_case_sync import UseCaseSync

DEFAULT_FILTER_ORDER = 8


class FilterType(StrEnum):
    BANDPASS = "bandpass"
    LOWPASS = "lowpass"
    HIGHPASS = "highpass"


@dataclass(frozen=True)
class FilterSpec:
    """Filter parameters. `low` is the lower band edge (bandpass) or the
    cutoff (highpass); `high` is the upper band edge (bandpass) or the cutoff
    (lowpass)."""

    type: FilterType
    low: float | None = None
    high: float | None = None
    order: int = DEFAULT_FILTER_ORDER

    def bounds(self) -> float | list[float]:
        if self.type == FilterType.BANDPASS:
            if self.low is None or self.high is None:
                raise ValueError("Bandpass needs low and high edges")
            return [self.low, self.high]
        cutoff = self.high if self.type == FilterType.LOWPASS else self.low
        if cutoff is None:
            raise ValueError("Filter needs a cutoff")
        return cutoff


class FilterAudio(UseCaseSync[np.ndarray]):
    """Zero-phase Butterworth filter (forward-backward second-order sections)."""

    def __init__(self, x: np.ndarray, fs: int, spec: FilterSpec):
        super().__init__()
        self.x = x
        self.fs = fs
        self.spec = spec

    def invoke(self) -> np.ndarray:
        sos = butter(
            self.spec.order,
            self.spec.bounds(),
            fs=self.fs,
            btype=str(self.spec.type),
            output="sos",
        )
        return sosfiltfilt(sos, self.x).astype(self.x.dtype, copy=False)
