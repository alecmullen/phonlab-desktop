import phonlab as phon

from core.base.use_case import UseCase
from core.track_formants.ifc_lock import IFC_LOCK


class WarmUpFormantTracking(UseCase[None]):
    """Load (or compile) phonlab's numba code for IFC_formants ahead of time,
    which otherwise delays the first formant tracking of a session by seconds."""

    def __call__(self):
        with IFC_LOCK:
            phon.ifc_warmup_numba(verbose=False)
        yield None
