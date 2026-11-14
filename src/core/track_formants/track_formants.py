import numpy as np
import phonlab as phon

from core.base.use_case import UseCase
from core.track_formants.entity.formant_track import FormantTrack
from res.constants import FORMANT_PREEMPHASIS, FORMANT_SPEAKER

FORMANT_COLUMNS = ["F1", "F2", "F3", "F4"]


class TrackFormants(UseCase[FormantTrack]):
    def __call__(
        self,
        x: np.ndarray,
        fs: int,
        preemph: float = FORMANT_PREEMPHASIS,
        speaker: int = FORMANT_SPEAKER,
    ):
        df = phon.IFC_formants(x, fs, preemph=preemph, speaker=speaker)
        yield FormantTrack(
            df["sec"].to_numpy(dtype=float), df[FORMANT_COLUMNS].to_numpy(dtype=float)
        )
