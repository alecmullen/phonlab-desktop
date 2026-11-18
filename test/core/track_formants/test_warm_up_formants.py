import pytest

import core.track_formants.warm_up_formants as warm_up_module
from core.track_formants.formant_lock import FORMANT_LOCK
from core.track_formants.warm_up_formants import WarmUpFormantTracking


def test_call_runs_phon_warm_up_quietly_while_holding_the_ifc_lock(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = []

    def fake_warm_up(verbose: bool):
        calls.append({"verbose": verbose, "locked": FORMANT_LOCK.locked()})

    monkeypatch.setattr(warm_up_module.phon, "ifc_warmup_numba", fake_warm_up)

    WarmUpFormantTracking().run_sync()

    assert calls == [{"verbose": False, "locked": True}]
    assert not FORMANT_LOCK.locked()
