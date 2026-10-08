import numpy as np
from scipy.signal import butter, sosfiltfilt

from core.base.use_case_sync import UseCaseSync
from core.transform_audio.entity.filter_spec import FilterSpec


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
