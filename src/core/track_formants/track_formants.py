import numpy as np
import phonlab as phon

from core.base.use_case import UseCase
from core.track_formants.entity.formant_track import FormantTrack
from res.constants import (
    FORMANT_F0_MAX,
    FORMANT_F0_MIN,
    FORMANT_PREEMPHASIS,
    FORMANT_SPEAKER,
)

FORMANT_COLUMNS = ["F1", "F2", "F3", "F4"]


class TrackFormants(UseCase[FormantTrack]):
    def __init__(
        self,
        x: np.ndarray,
        fs: int,
        preemphasis: float = FORMANT_PREEMPHASIS,
        f0_min: float = FORMANT_F0_MIN,
        f0_max: float = FORMANT_F0_MAX,
        speaker: int = FORMANT_SPEAKER,
    ):
        self.x = x
        self.fs = fs
        self.preemphasis = preemphasis
        self.f0_min = f0_min
        self.f0_max = f0_max
        self.speaker = speaker

    def invoke(self):
        df = phon.track_formants(
            self.x,
            self.fs,
            method="ifc",
            preemphasis=self.preemphasis,
            f0_range=[self.f0_min, self.f0_max],
            speaker=self.speaker,
            quiet=True,
        )
        yield FormantTrack(
            df["sec"].to_numpy(dtype=float), df[FORMANT_COLUMNS].to_numpy(dtype=float)
        )

    def stop(self):
        pass
