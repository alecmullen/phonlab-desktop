from ui.document.state.plot_layout_state import PlotLayoutState, PlotType


def test_default_state_has_only_waveform():
    state = PlotLayoutState()

    assert state.has_waveform() is True
    assert state.has_spectrogram() is False
    assert state.has_annotation() is False


def test_has_waveform_reflects_plot_membership():
    assert PlotLayoutState(plots={PlotType.WAVEFORM}).has_waveform() is True
    assert PlotLayoutState(plots={PlotType.SPECTROGRAM}).has_waveform() is False


def test_has_spectrogram_reflects_plot_membership():
    assert PlotLayoutState(plots={PlotType.SPECTROGRAM}).has_spectrogram() is True
    assert PlotLayoutState(plots={PlotType.WAVEFORM}).has_spectrogram() is False


def test_has_annotation_reflects_plot_membership():
    assert PlotLayoutState(plots={PlotType.ANNOTATION}).has_annotation() is True
    assert PlotLayoutState(plots={PlotType.WAVEFORM}).has_annotation() is False


def test_all_plot_types_can_be_combined():
    state = PlotLayoutState(
        plots={PlotType.WAVEFORM, PlotType.SPECTROGRAM, PlotType.ANNOTATION}
    )

    assert state.has_waveform() is True
    assert state.has_spectrogram() is True
    assert state.has_annotation() is True
