import pytest

from core.track_formants.entity.formant_method import FormantMethod
from core.track_formants.entity.formant_options import FormantOptions
from ui.spectrogram.state.formant_settings import (
    FormantMethodState,
    FormantSettingsState,
    to_formant_options,
)


def test_defaults_are_ifc_with_a_medium_vocal_tract():
    settings = FormantSettingsState()

    assert settings.method == FormantMethodState.IFC
    assert (settings.preemphasis, settings.speaker) == (0.94, 1)
    assert settings.order == -1


@pytest.mark.parametrize(
    "method, preemphasis",
    [("ifc", 0.94), ("lpc", 0.94), ("rlpc", 0.94), ("tvlp", 0.95), ("dppt", 0.0)],
)
def test_with_method_uses_that_methods_preemphasis(method: str, preemphasis: float):
    settings = FormantSettingsState(preemphasis=0.5, speaker=2).with_method(
        FormantMethodState(method)
    )

    assert settings.method == method
    assert settings.preemphasis == preemphasis
    assert settings.speaker == 2  # the rest is kept


def test_method_states_mirror_core_methods():
    assert [m.value for m in FormantMethodState] == [m.value for m in FormantMethod]


def test_to_formant_options_maps_every_field():
    settings = FormantSettingsState(
        FormantMethodState.RLPC, 0.9, 2, 12, 7000, 150, 1000, 0.005, 0.04, True, 0.6
    )

    assert to_formant_options(settings) == FormantOptions(
        FormantMethod.RLPC, 0.9, 2, 12, 7000, 150, 1000, 0.005, 0.04, True, 0.6
    )


@pytest.mark.parametrize(
    "method, length",
    [("ifc", 0.03), ("lpc", 0.03), ("rlpc", 0.03), ("tvlp", 0.1), ("dppt", 0.03)],
)
def test_with_method_uses_that_methods_window_length(method: str, length: float):
    settings = FormantSettingsState(step=0.005, length=0.05, voiced_only=True)

    changed = settings.with_method(FormantMethodState(method))

    assert changed.length == length
    assert changed.step == 0.005  # the rest is kept
    assert changed.voiced_only
