import numpy as np
import pandas as pd
import pytest

import core.track_formants.track_formants as track_formants_module
from core.track_formants.ifc_lock import IFC_LOCK
from core.track_formants.track_formants import TrackFormants

FS = 1000


@pytest.fixture
def short_chunks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(track_formants_module, "FORMANT_CHUNK_SEC", 3)
    monkeypatch.setattr(track_formants_module, "FORMANT_CHUNK_OVERLAP_SEC", 1)


@pytest.fixture
def ifc_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """A fake IFC_formants that, like the real one, measures every 10 ms from
    0.01 s. Its audio is the ramp `np.arange(n) / FS`, so a segment's first
    sample says where in the file it starts, and each frame's F1 is set to its
    absolute time (x 1000) to show that frames are placed correctly."""
    calls = []

    def fake_ifc_formants(
        x: np.ndarray, fs: int, preemph: float, speaker: int
    ) -> pd.DataFrame:
        calls.append(
            {"start": x[0] if len(x) else None, "fs": fs, "preemph": preemph,
             "speaker": speaker, "locked": IFC_LOCK.locked()}
        )  # fmt: skip
        sec = np.arange(0.01, len(x) / fs - 0.02, 0.01)
        start = x[0] if len(x) else 0.0
        f = (start + sec) * 1000
        return pd.DataFrame(
            {"sec": sec, "F1": f, "F2": f + 1, "F3": f + 2, "F4": f + 3}
        )

    monkeypatch.setattr(track_formants_module.phon, "IFC_formants", fake_ifc_formants)
    return calls


def ramp(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * FS)) / FS


def test_short_file_is_one_chunk_with_the_params(ifc_calls: list[dict]):
    chunks = list(TrackFormants()(ramp(2), FS, 0.9, 2))

    assert len(chunks) == 1
    assert ifc_calls == [
        {"start": 0.0, "fs": FS, "preemph": 0.9, "speaker": 2, "locked": True}
    ]
    np.testing.assert_allclose(chunks[0].sec[:3], [0.01, 0.02, 0.03])
    np.testing.assert_allclose(chunks[0].formants[:2, 0], [10, 20])
    np.testing.assert_allclose(chunks[0].formants[0], [10, 11, 12, 13])


def test_chunks_cover_the_file_exactly_once(short_chunks: None, ifc_calls: list[dict]):
    chunks = list(TrackFormants()(ramp(10), FS))

    assert len(chunks) == 4  # 3 s chunks: 0-3, 3-6, 6-9, 9-
    sec = np.concatenate([c.sec for c in chunks])
    assert len(np.unique(np.round(sec, 6))) == len(sec)  # no frame twice
    all_secs = np.sort(sec)
    np.testing.assert_allclose(np.diff(all_secs), 0.01, atol=1e-9)  # no gaps
    # frames sit at their true times, whichever chunk measured them
    for chunk in chunks:
        np.testing.assert_allclose(chunk.formants[:, 0], chunk.sec * 1000, atol=1e-6)


def test_chunk_analyzes_a_second_of_overlap_each_side(
    short_chunks: None, ifc_calls: list[dict]
):
    list(TrackFormants()(ramp(10), FS))

    starts = sorted(call["start"] for call in ifc_calls)
    assert starts == [0.0, 2.0, 5.0, 8.0]  # chunk starts 0, 3, 6, 9 minus 1 s


def test_chunks_are_yielded_outward_from_the_priority_time(
    short_chunks: None, ifc_calls: list[dict]
):
    chunks = list(TrackFormants()(ramp(12), FS, priority_sec=7.0))

    # chunk 2 (6-9 s) first, then its neighbors (later one first), then chunk 0
    assert [round(c.sec[0]) for c in chunks] == [6, 9, 3, 0]


def test_priority_past_the_end_starts_at_the_last_chunk(
    short_chunks: None, ifc_calls: list[dict]
):
    chunks = list(TrackFormants()(ramp(7), FS, priority_sec=500.0))

    assert round(chunks[0].sec[0]) == 6


def test_track_columns_are_f1_to_f4(ifc_calls: list[dict]):
    chunk = next(TrackFormants()(ramp(1), FS))

    assert chunk.formants.shape[1] == 4
