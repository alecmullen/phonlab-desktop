import math

import numpy as np

from core.base.use_case import UseCase
from core.track_formants.entity.formant_options import FormantOptions
from core.track_formants.entity.formant_track import FormantTrack
from core.track_formants.measure_formants import (
    FORMANT_COLUMNS,
    ORDER_METHODS,
    measure_formants,
    with_chosen_order,
)
from res.constants import FORMANT_CHUNK_OVERLAP_SEC, FORMANT_CHUNK_SEC


class TrackFormants(UseCase[FormantTrack]):
    """Track the formants of a whole file, a chunk at a time. Each yielded
    FormantTrack holds the frames of one chunk, timed from the start of `x`.
    Chunks are yielded outward from the one containing `priority_sec`, so the
    part of the file being looked at is measured first."""

    def __call__(
        self,
        x: np.ndarray,
        fs: int,
        options: FormantOptions | None = None,
        priority_sec: float = 0.0,
    ):
        options = options or FormantOptions()
        duration = len(x) / fs
        n_chunks = max(1, math.ceil(duration / FORMANT_CHUNK_SEC))
        first = min(int(priority_sec // FORMANT_CHUNK_SEC), n_chunks - 1)
        # nearest chunks first; the later chunk when two are equally near
        order = sorted(range(n_chunks), key=lambda k: (abs(k - first), k < first))

        # An automatic LPC order is chosen from the first chunk, the part of
        # the file being looked at, and used for every chunk
        first_segment, _ = self._segment(x, fs, order[0])
        options = with_chosen_order(first_segment, fs, options)

        for k in order:
            yield self._track_chunk(x, fs, options, k, k == n_chunks - 1)

    @staticmethod
    def _segment(x: np.ndarray, fs: int, k: int) -> tuple[np.ndarray, int]:
        """The audio to analyze for chunk `k`, and where it starts in seconds.
        It extends a little before and after the chunk so the chunk's edge
        frames are measured with their full context. Chunk and overlap are
        whole seconds, so analysis starts on a sample and on the 10 ms frame
        grid."""
        chunk_start = k * FORMANT_CHUNK_SEC
        analysis_start = max(0, chunk_start - FORMANT_CHUNK_OVERLAP_SEC)
        analysis_end = chunk_start + FORMANT_CHUNK_SEC + FORMANT_CHUNK_OVERLAP_SEC
        return x[analysis_start * fs : analysis_end * fs], analysis_start

    def _track_chunk(
        self,
        x: np.ndarray,
        fs: int,
        options: FormantOptions,
        k: int,
        is_last: bool,
    ) -> FormantTrack:
        chunk_start = k * FORMANT_CHUNK_SEC
        chunk_end = chunk_start + FORMANT_CHUNK_SEC
        segment, analysis_start = self._segment(x, fs, k)

        df = measure_formants(segment, fs, options)

        # Methods put their frames at different offsets on the 10 ms grid
        # (IFC on it, the others half a frame after it), but all on the same
        # grid whichever chunk measures them. Rounding off floating point
        # noise lets a frame exactly on a chunk boundary go to the right chunk.
        sec = np.round(df["sec"].to_numpy(dtype=float) + analysis_start, 6)
        # the last chunk keeps everything to the end of the file
        keep = (sec >= chunk_start) & (is_last | (sec < chunk_end))
        return FormantTrack(
            sec[keep],
            df[FORMANT_COLUMNS].to_numpy(dtype=float)[keep],
            max(options.order, 0) if options.method in ORDER_METHODS else 0,
        )
