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
    def __call__(
        self,
        x: np.ndarray,
        fs: int,
        preemphasis: float = FORMANT_PREEMPHASIS,
        f0_min: float = FORMANT_F0_MIN,
        f0_max: float = FORMANT_F0_MAX,
        speaker: int = FORMANT_SPEAKER,
    ):
        df = phon.track_formants(
            x,
            fs,
            method="ifc",
            preemphasis=preemphasis,
            f0_range=[f0_min, f0_max],
            speaker=speaker,
            quiet=True,
        )
        yield FormantTrack(
            df["sec"].to_numpy(dtype=float), df[FORMANT_COLUMNS].to_numpy(dtype=float)
        )
