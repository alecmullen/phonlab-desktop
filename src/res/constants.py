from ui.document.state.plot_layout_state import PlotType

# -- Settings files --
PROJECT_FILE_NAME = "phonlab.toml"
DISPLAY_SECTION = "display"
PLAN_KEY = "plan"

# -- Files --
# Suffixes are matched case-insensitively, so .wav, .WAV, .Wav, ... all count
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

# -- Formant Tracking --
# Preemphasis each formant method works best with, by FormantMethod value
FORMANT_PREEMPHASIS = {
    "ifc": 0.94,
    "lpc": 0.94,
    "rlpc": 0.94,
    "tvlp": 0.95,
    "dppt": 0.0,
}
FORMANT_STEP_SEC = 0.01
# Analysis window length each formant method works best with. IFC has no
# window length setting, so its entry only fills the dialog's field.
FORMANT_LENGTH_SEC = {
    "ifc": 0.03,
    "lpc": 0.03,
    "rlpc": 0.03,
    "tvlp": 0.1,
    "dppt": 0.03,
}
FORMANT_VOICING_THRESHOLD = 0.8  # phon.VAD() probability to count a frame as voiced
PHONLAB_DOCS_URL = "https://phonlab.readthedocs.io/en/latest/"
# Documentation page of each formant method, by FormantMethod value
FORMANT_DOCS = {
    "ifc": "acoustphon.html#phonlab.IFC_formants",
    "lpc": "acoustphon.html#phonlab.LPC_formants",
    "rlpc": "acoustphon.html#phonlab.RLPC_formants",
    "tvlp": "acoustphon.html#phonlab.TVLP_formants",
    "dppt": "acoustphon.html#phonlab.DPPT_formants",
}
FORMANT_SPEAKER = 1  # 0 = long vocal tract, 1 = medium, 2 = short
FORMANT_AUTO_ORDER = -1  # let phonlab choose the LPC order
FORMANT_MIN_ORDER = 6
FORMANT_MAX_ORDER = 30
FORMANT_TOP_FREQUENCY = 6000  # RLPC and TVLP resample to twice this rate
FORMANT_MEDIAN_F0 = 200  # TVLP's expected median pitch, in Hz
FORMANT_DELTA_F = 1100  # DPPT's expected spacing between formants, in Hz
# LPC_formants always analyzes audio resampled to this rate
FORMANT_LPC_SAMPLE_RATE = 12000
# Formants are tracked a chunk at a time. Both are whole seconds, so chunks
# start on the 10 ms frame grid and on a sample at any sampling rate.
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
