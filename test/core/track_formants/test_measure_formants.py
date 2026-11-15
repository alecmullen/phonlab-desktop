from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

import core.track_formants.measure_formants as measure_formants_module
from core.track_formants.entity.formant_method import FormantMethod
from core.track_formants.entity.formant_options import FormantOptions
from core.track_formants.formant_lock import FORMANT_LOCK
from core.track_formants.measure_formants import measure_formants, with_chosen_order

X = np.zeros(1000)
FS = 1000


def frames() -> pd.DataFrame:
    return pd.DataFrame(
        {"sec": [0.01, 0.02], "F1": [1.0, 2.0], "F2": [3.0, 4.0], "F3": [5.0, 6.0],
         "F4": [7.0, 8.0], "F5": [9.0, 9.0], "BW1": [1.0, 1.0]}
    )  # fmt: skip


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict]]:
    """Fake phonlab formant functions that record how they were called"""
    recorded = []

    def fake(
        name: str, returns_tuple: bool = False
    ) -> Callable[..., pd.DataFrame | tuple[pd.DataFrame, np.ndarray]]:
        def call(
            x: np.ndarray, fs: int, **kwargs: object
        ) -> pd.DataFrame | tuple[pd.DataFrame, np.ndarray]:
            recorded.append((name, {**kwargs, "locked": FORMANT_LOCK.locked()}))
            return (frames(), np.zeros(1)) if returns_tuple else frames()

        return call

    phon = measure_formants_module.phon
    monkeypatch.setattr(phon, "IFC_formants", fake("IFC"))
    monkeypatch.setattr(phon, "LPC_formants", fake("LPC"))
    monkeypatch.setattr(phon, "RLPC_formants", fake("RLPC", returns_tuple=True))
    monkeypatch.setattr(phon, "TVLP_formants", fake("TVLP"))
    monkeypatch.setattr(phon, "DPPT_formants", fake("DPPT"))
    return recorded


@pytest.mark.parametrize(
    "options, name, expected",
    [
        (FormantOptions(preemphasis=0.9, speaker=2), "IFC",
         {"preemph": 0.9, "speaker": 2}),
        (FormantOptions(FormantMethod.LPC, 0.9, order=12), "LPC",
         {"preemph": 0.9, "order": 12, "step": 0.01, "length": 0.03}),
        (FormantOptions(FormantMethod.RLPC, 0.9, order=10, top_frequency=8000), "RLPC",
         {"preemph": 0.9, "order": 10, "tf": 8000, "step": 0.01, "length": 0.03}),
        (FormantOptions(FormantMethod.TVLP, 0.95, order=-1, top_frequency=7000,
                        median_f0=120, length=0.1), "TVLP",
         {"preemph": 0.95, "order": -1, "tf": 7000, "f0median": 120,
          "step": 0.01, "length": 0.1}),
        (FormantOptions(FormantMethod.DPPT, 0.0, delta_f=900), "DPPT",
         {"preemph": 0.0, "deltaF": 900, "step": 0.01, "length": 0.03}),
    ],
)  # fmt: skip
def test_each_method_calls_its_phonlab_function_with_its_parameters(
    calls: list, options: FormantOptions, name: str, expected: dict
):
    measure_formants(X, FS, options)

    assert calls == [(name, {**expected, "locked": True})]


@pytest.fixture
def order_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    recorded = []

    def fake_prep_audio(
        x: np.ndarray, fs: int, **kwargs: int
    ) -> tuple[np.ndarray, int]:
        recorded.append(kwargs)
        return x, kwargs["target_fs"]

    monkeypatch.setattr(measure_formants_module.phon, "prep_audio", fake_prep_audio)
    monkeypatch.setattr(
        measure_formants_module.phon,
        "choose_order",
        lambda x, fs, *length: (
            recorded.append({"fs": fs, "length": length}) or 13,
            0.1,
        ),
    )
    return recorded


def test_order_is_chosen_from_audio_prepared_as_lpc_formants_does(order_calls: list):
    options = FormantOptions(FormantMethod.LPC, 0.9)

    assert with_chosen_order(X, FS, options).order == 13

    assert order_calls == [
        {"target_fs": 12000, "preemph": 0.9, "scale": True, "fix_polarity": False},
        {"fs": 12000, "length": (0.03,)},
    ]


@pytest.mark.parametrize("method", [FormantMethod.RLPC, FormantMethod.TVLP])
def test_order_for_rlpc_and_tvlp_is_chosen_at_twice_the_top_frequency(
    order_calls: list, method: FormantMethod
):
    options = FormantOptions(method, 0.9, top_frequency=7000)

    assert with_chosen_order(X, FS, options).order == 13

    assert order_calls[0]["target_fs"] == 14000
    assert order_calls[0]["fix_polarity"] is True
    # TVLP's long frames are not given to choose_order()
    assert order_calls[1]["length"] == (() if method == FormantMethod.TVLP else (0.03,))


@pytest.mark.parametrize(
    "options",
    [
        FormantOptions(FormantMethod.LPC, order=12),  # already chosen
        FormantOptions(FormantMethod.IFC),  # has no order
        FormantOptions(FormantMethod.DPPT),
    ],
)
def test_order_is_left_alone_when_chosen_or_unused(
    order_calls: list, options: FormantOptions
):
    assert with_chosen_order(X, FS, options) == options
    assert order_calls == []


def test_voiced_only_blanks_the_formants_of_voiceless_frames(
    calls: list, monkeypatch: pytest.MonkeyPatch
):
    vad_calls = []

    def fake_vad(x: np.ndarray, fs: int, threshold: float) -> pd.DataFrame:
        vad_calls.append(threshold)
        return pd.DataFrame({"sec": [0.01, 0.02], "voiced": [True, False]})

    monkeypatch.setattr(measure_formants_module.phon, "VAD", fake_vad)

    df = measure_formants(X, FS, FormantOptions(FormantMethod.LPC, voiced_only=True))

    assert vad_calls == [0.5]  # the default threshold
    assert df["F1"].iloc[0] == 1.0
    assert df.loc[1, ["F1", "F2", "F3", "F4"]].isna().all()
    assert list(df.columns) == ["sec", "F1", "F2", "F3", "F4"]


def test_voiced_only_uses_the_voicing_threshold(
    calls: list, monkeypatch: pytest.MonkeyPatch
):
    thresholds = []

    def fake_vad(x: np.ndarray, fs: int, threshold: float) -> pd.DataFrame:
        thresholds.append(threshold)
        return pd.DataFrame({"sec": [0.01, 0.02], "voiced": [True, True]})

    monkeypatch.setattr(measure_formants_module.phon, "VAD", fake_vad)

    options = FormantOptions(FormantMethod.LPC, voiced_only=True, voicing_threshold=0.6)
    measure_formants(X, FS, options)

    assert thresholds == [0.6]


def test_formants_a_method_did_not_find_are_nan_columns(
    monkeypatch: pytest.MonkeyPatch,
):
    """A low LPC order makes LPC_formants return only F1 and F2"""
    few = pd.DataFrame({"sec": [0.01, 0.02], "F1": [1.0, 2.0], "F2": [3.0, 4.0]})
    monkeypatch.setattr(
        measure_formants_module.phon, "LPC_formants", lambda x, fs, **kwargs: few
    )

    df = measure_formants(X, FS, FormantOptions(FormantMethod.LPC, order=4))

    assert list(df.columns) == ["sec", "F1", "F2", "F3", "F4"]
    assert df["F2"].tolist() == [3.0, 4.0]
    assert df[["F3", "F4"]].isna().all().all()


def test_missing_formants_do_not_stop_voiced_only(monkeypatch: pytest.MonkeyPatch):
    few = pd.DataFrame({"sec": [0.01, 0.02], "F1": [1.0, 2.0]})
    monkeypatch.setattr(
        measure_formants_module.phon, "LPC_formants", lambda x, fs, **kwargs: few
    )
    monkeypatch.setattr(
        measure_formants_module.phon,
        "VAD",
        lambda x, fs, threshold: pd.DataFrame(
            {"sec": [0.01, 0.02], "voiced": [False, True]}
        ),
    )

    df = measure_formants(X, FS, FormantOptions(FormantMethod.LPC, voiced_only=True))

    assert np.isnan(df.loc[0, "F1"])
    assert df.loc[1, "F1"] == 2.0
