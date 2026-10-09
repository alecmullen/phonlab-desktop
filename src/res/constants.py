from ui.document.state.plot_layout_state import PlotType

# -- Document Window --
DEFAULT_WINDOW_LENGTH = 10
PLOT_ROW_SPACING = 8
PLOT_ROW_WEIGHT = {
    PlotType.WAVEFORM: 50,
    PlotType.SPECTROGRAM: 100,
    PlotType.ANNOTATION: 50,
}

# -- Document Plot --
LEFT_AXIS_WIDTH = 70

# -- Audio Editing --
MAX_UNDO_HISTORY = 10
ZERO_CROSSING_SEARCH_MS = 5

# -- Audio Player --
LATENCY_WARNING_THRESHOLD_S = 0.1
# Silence added around played audio. Freshly opened output streams (especially
# Bluetooth) can drop the first samples while the device wakes up, and the tail
# can be cut off when the stream is closed, so make sure only silence is lost.
PLAYBACK_PRE_ROLL_S = 0.0
PLAYBACK_POST_ROLL_S = 0.5
# Safety net for waiting on the stream to finish; allows for the variable delay
# before the first audio callback.
PLAYBACK_FINISH_TIMEOUT_MARGIN_S = 2.0

# -- Spectrogram --
MAX_SGRAM_LENGTH = 10
DEFAULT_GRAY_CUTOFF = 0.6
SPECTROGRAM_PRE_EMPHASIS = 0.94
SPECTROGRAM_LOW_PERCENTILE = 20
SPECTROGRAM_HIGH_PERCENTILE = 80
SPECTROGRAM_PERCENTILE_SAMPLE_SIZE = 100_000

# -- Annotations --
NODE_V_MARGIN = 7
NODE_H_MARGIN = 5
POINT_LABEL_WIDTH = 100
LABEL_HEIGHT_RATIO = 0.8
