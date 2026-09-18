from ui.spectrogram.state.spectrogram_settings import SpectrogramSettingsState


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
