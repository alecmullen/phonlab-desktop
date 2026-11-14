import pytest

from ui.spectrogram.state.spectrogram_settings import (
    SpectrogramSettingsState,
    SpectrogramTypeState,
)


def test_post_init_keeps_order_when_above_minimum():
    state = SpectrogramSettingsState(fs=16000, window_size=0.008, order=9)

    assert state.order == 9


def test_post_init_raises_order_to_minimum_when_below_minimum():
    state = SpectrogramSettingsState(fs=16000, window_size=0.008, order=1)

    # nperseg = 128 -> floor(log2(128)) + 1 == 8
    assert state.order == 8


def test_post_init_computes_minimum_from_fs_and_window_size():
    state = SpectrogramSettingsState(fs=8000, window_size=0.032, order=1)

    # nperseg = 256 -> floor(log2(256)) + 1 == 9
    assert state.order == 9


def test_type_defaults_to_fft():
    assert SpectrogramSettingsState().type == SpectrogramTypeState.FFT


@pytest.mark.parametrize(
    ("type", "window_size", "step_size"),
    [
        (SpectrogramTypeState.FFT, 0.008, 0.001),
        (SpectrogramTypeState.MULTITAPER, 0.02, 0.004),
        (SpectrogramTypeState.CEPSTRAL, 0.04, 0.004),
        (SpectrogramTypeState.LPC, 0.03, 0.004),
        (SpectrogramTypeState.MEL, 0.064, 0.001),
    ],
)
def test_with_type_takes_the_window_and_step_usual_for_the_type(
    type: SpectrogramTypeState, window_size: float, step_size: float
):
    # Whatever the other types take, they are slower than the FFT, so they step 4 ms
    state = SpectrogramSettingsState(window_size=0.05, step_size=0.002).with_type(type)

    assert state.type == type
    assert state.window_size == window_size
    assert state.step_size == step_size


def test_with_type_keeps_the_sample_rate_and_raises_order_for_the_new_window():
    state = SpectrogramSettingsState(fs=32000, order=9).with_type(
        SpectrogramTypeState.CEPSTRAL
    )

    assert state.fs == 32000
    # nperseg = 1280 -> floor(log2(1280)) + 1 == 11
    assert state.order == 11


def test_with_type_lowers_the_order_again_when_the_new_window_is_shorter():
    cepstral = SpectrogramSettingsState(fs=32000).with_type(
        SpectrogramTypeState.CEPSTRAL
    )

    fft = cepstral.with_type(SpectrogramTypeState.FFT)

    assert cepstral.order == 11
    # nperseg = 256 -> floor(log2(256)) + 1 == 9
    assert fft.order == 9


def test_order_is_a_whole_number():
    # phonlab uses it as an exponent: it must not turn into a numpy float
    state = SpectrogramSettingsState(fs=16000, window_size=0.04, order=1)

    assert type(state.order) is int


def test_mel_needs_a_sample_rate_that_holds_its_filters():
    # They reach 7600 Hz, so a top frequency of at least 8000
    low = SpectrogramSettingsState(fs=8000, type=SpectrogramTypeState.MEL)
    high = SpectrogramSettingsState(fs=24000, type=SpectrogramTypeState.MEL)

    assert low.fs == 16000
    assert high.fs == 24000


def test_with_type_mel_raises_a_low_sample_rate():
    state = SpectrogramSettingsState(fs=8000).with_type(SpectrogramTypeState.MEL)

    assert state.fs == 16000


def test_other_types_keep_a_low_sample_rate():
    state = SpectrogramSettingsState(fs=8000, type=SpectrogramTypeState.LPC)

    assert state.fs == 8000


def test_nw_and_lift_default_to_phonlabs_usual_values():
    settings = SpectrogramSettingsState()

    assert settings.multitaper_nw == 3.0
    assert settings.cepstral_lift == 0.003
