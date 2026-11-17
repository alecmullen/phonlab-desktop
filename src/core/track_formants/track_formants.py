import math

import numpy as np
import phonlab as phon

from core.base.use_case import UseCase
from core.track_formants.entity.formant_track import FormantTrack
from core.track_formants.ifc_lock import IFC_LOCK
from res.constants import (
    FORMANT_CHUNK_OVERLAP_SEC,
    FORMANT_CHUNK_SEC,
    FORMANT_PREEMPHASIS,
)
from ui.spectrogram.state.formant_settings import FormantSpeakerType

FORMANT_COLUMNS = ["F1", "F2", "F3", "F4"]
FRAMES_PER_SEC = 100  # IFC_formants measures every 10 ms, on a 10 ms grid


class TrackFormants(UseCase[FormantTrack]):
    """Track the formants of a whole file, a chunk at a time. Each yielded
    FormantTrack holds the frames of one chunk, timed from the start of `x`.
    Chunks are yielded outward from the one containing `priority_sec`, so the
    part of the file being looked at is measured first."""

    def __call__(
        self,
        x: np.ndarray,
        fs: int,
        preemph: float = FORMANT_PREEMPHASIS,
        speaker: FormantSpeakerType = FormantSpeakerType.MEDIUM,
        priority_sec: float = 0.0,
    ):
        duration = len(x) / fs
        n_chunks = max(1, math.ceil(duration / FORMANT_CHUNK_SEC))
        first = min(int(priority_sec // FORMANT_CHUNK_SEC), n_chunks - 1)
        # nearest chunks first; the later chunk when two are equally near
        order = sorted(range(n_chunks), key=lambda k: (abs(k - first), k < first))

        for k in order:
            yield self._track_chunk(x, fs, preemph, speaker.value, k, k == n_chunks - 1)

    def _track_chunk(
        self,
        x: np.ndarray,
        fs: int,
        preemph: float,
        speaker: int,
        k: int,
        is_last: bool,
    ) -> FormantTrack:
        chunk_start = k * FORMANT_CHUNK_SEC
        chunk_end = chunk_start + FORMANT_CHUNK_SEC

        # Analyze a little before and after the chunk so its edge frames are
        # measured with their full context
        analysis_start = max(0, chunk_start - FORMANT_CHUNK_OVERLAP_SEC)
        analysis_end = chunk_end + FORMANT_CHUNK_OVERLAP_SEC
        segment = x[analysis_start * fs : analysis_end * fs]

        with IFC_LOCK:
            df = phon.IFC_formants(segment, fs, preemph=preemph, speaker=speaker)

        frame = np.round(
            (df["sec"].to_numpy(dtype=float) + analysis_start) * FRAMES_PER_SEC
        )
        # the last chunk keeps everything to the end of the file
        keep = (frame >= chunk_start * FRAMES_PER_SEC) & (
            is_last | (frame < chunk_end * FRAMES_PER_SEC)
        )
        return FormantTrack(
            frame[keep] / FRAMES_PER_SEC,
            df[FORMANT_COLUMNS].to_numpy(dtype=float)[keep],
        )
