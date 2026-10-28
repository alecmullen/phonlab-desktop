import numpy as np
import pandas as pd
import pytest

import core.track_formants.track_formants as track_formants_module
from core.track_formants.track_formants import TrackFormants


def test_invoke_calls_phon_track_formants_with_ifc_and_params(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = []

    def fake_track_formants(x: np.ndarray, fs: int, **kwargs: object) -> pd.DataFrame:
        calls.append((x, fs, kwargs))
        return pd.DataFrame(
            {
                "sec": [0.01, 0.02],
                "rms": [-10.0, -11.0],
                "F1": [500.0, 510.0],
                "F2": [1500.0, 1510.0],
                "F3": [2500.0, 2510.0],
                "F4": [3500.0, 3510.0],
                "f0": [100.0, 101.0],
                "c": [0.5, 0.6],
            }
        )

    monkeypatch.setattr(
        track_formants_module.phon, "track_formants", fake_track_formants
    )
    x = np.arange(10, dtype=np.float64)

    result = TrackFormants().run_sync(x, 8000, 0.9, 80, 300, 2)

    assert len(calls) == 1
    assert calls[0][0] is x
    assert calls[0][1] == 8000
    assert calls[0][2] == {
        "method": "ifc",
        "preemphasis": 0.9,
        "f0_range": [80, 300],
        "speaker": 2,
        "quiet": True,
    }
    np.testing.assert_array_equal(result.sec, [0.01, 0.02])
    np.testing.assert_array_equal(
        result.formants, [[500, 1500, 2500, 3500], [510, 1510, 2510, 3510]]
    )
