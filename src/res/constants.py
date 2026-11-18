from ui.document.state.plot_layout_state import PlotType

# -- Mouse --
DOUBLE_CLICK_INTERVAL_MS = 250

# -- Settings files --
PROJECT_FILE_NAME = "phonlab.toml"
DISPLAY_SECTION = "display"
PLAN_KEY = "plan"

# -- Files --
AUDIO_FILE_SUFFIXES = (".wav",)
TEXTGRID_FILE_SUFFIXES = (".textgrid",)
PROJECT_DATABASE_FILENAME = "phonlab.db"

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
PLAYBACK_POST_ROLL_S = 0.5
PLAYBACK_FINISH_TIMEOUT_MARGIN_S = 2.0

# -- Spectrogram --
MAX_SGRAM_LENGTH = 10
DEFAULT_GRAY_CUTOFF = 0.6
SPECTROGRAM_PRE_EMPHASIS = 0.94
SPECTROGRAM_LOW_PERCENTILE = 20
SPECTROGRAM_HIGH_PERCENTILE = 80
SPECTROGRAM_PERCENTILE_SAMPLE_SIZE = 100_000
SPECTROGRAM_WINDOW_SEC = {
    "fft": 0.008,
    "multitaper": 0.02,
    "cepstral": 0.04,
    "lpc": 0.03,
}
SPECTROGRAM_STEP_SEC = {
    "fft": 0.001,
    "multitaper": 0.004,
    "cepstral": 0.004,
    "lpc": 0.004,
}
CEPSTRAL_SEGMENT_SEC = 5

# -- Formant Tracking --
FORMANT_PREEMPHASIS = {
    "ifc": 0.94,
    "lpc": 0.94,
    "rlpc": 0.94,
    "tvlp": 0.95,
    "dppt": 0.0,
}
FORMANT_STEP_SEC = 0.01
FORMANT_LENGTH_SEC = {
    "ifc": 0.03,  # placeholder: IFC doesn't have window length setting
    "lpc": 0.03,
    "rlpc": 0.03,
    "tvlp": 0.1,
    "dppt": 0.03,
}
FORMANT_VOICING_THRESHOLD = 0.5
PHONLAB_DOCS_URL = "https://phonlab.readthedocs.io/en/latest/"
FORMANT_DOCS = {
    "ifc": "acoustphon.html#phonlab.IFC_formants",
    "lpc": "acoustphon.html#phonlab.LPC_formants",
    "rlpc": "acoustphon.html#phonlab.RLPC_formants",
    "tvlp": "acoustphon.html#phonlab.TVLP_formants",
    "dppt": "acoustphon.html#phonlab.DPPT_formants",
}
FORMANT_AUTO_ORDER = -1  # let phonlab choose the LPC order
FORMANT_MIN_ORDER = 6
FORMANT_MAX_ORDER = 30
FORMANT_TOP_FREQUENCY = 6000
FORMANT_MEDIAN_F0 = 200
FORMANT_DELTA_F = 1100
FORMANT_LPC_SAMPLE_RATE = 12000
FORMANT_CHUNK_SEC = 30
FORMANT_CHUNK_OVERLAP_SEC = 1

# -- Audio Processing __
DEFAULT_FILTER_ORDER = 8

# -- Annotations --
NODE_V_MARGIN = 7
NODE_H_MARGIN = 5
POINT_LABEL_WIDTH = 100
LABEL_HEIGHT_RATIO = 0.8
SAME_NODE_THRESHOLD = 0.005
SAME_NODE_PIXEL_THRESH = 7
