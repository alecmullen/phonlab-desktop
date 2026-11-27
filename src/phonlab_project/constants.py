"""Constants the readers, the project layout and the project database use: file
types, how annotation formats are told apart, and the thresholds of the layout
guesses. The desktop app has its own in res.constants."""

# Suffixes are matched case-insensitively, so .wav, .WAV, .Wav, ... all count
AUDIO_FILE_SUFFIXES = (".wav",)

TEXTGRID_FILE_SUFFIXES = (".textgrid",)

# Annotation files that can be opened with a single sound file
SINGLE_FILE_ANNOTATION_SUFFIXES = (*TEXTGRID_FILE_SUFFIXES, ".eaf", ".srt", ".cha")

SAME_NODE_THRESHOLD = 0.005

PROJECT_AUDIO_EXTENSIONS = (".wav",)

PROJECT_VIDEO_EXTENSIONS = (".mp4", ".m4v", ".mov", ".avi", ".mkv", ".webm", ".mpg")

# Primary annotation extension (casefolded) -> format name
ANNOTATION_FORMATS = {
    ".textgrid": "textgrid",
    ".words": "buckeye",
    ".wrd": "timit",
    ".eaf": "elan",
    ".srt": "srt",
    ".cha": "chat",
}

# Extensions a format's reader reads itself, so they are not extra data files
ANNOTATION_COMPANION_EXTENSIONS = {"buckeye": (".phones",), "timit": (".phn",)}

# Subtitles (.srt): the longest a talker's name at the start of one is taken to be, and
# the tier for subtitles with no talker named
SRT_TALKER_MAX_LENGTH = 40

SRT_NO_TALKER_TIER = "subtitles"

# CHAT (.cha) files name the speakers by role (`PAR`, `INV`), not by name. The speaker
# with this code is the talker the folder and file names give the recording; each
# other speaker is a different person in each file, named by the code and a number
# that counts up through the project (`INV1`, `INV2`...)
CHAT_TARGET_CODE = "PAR"

PROJECT_IGNORED_NAMES = ("phonlab.db", "phonlab.toml")

TALKER_FIELD_NAMES = ("talker", "speaker")

# In a filename template: allows any characters (or none) that are not kept
TEMPLATE_IGNORE_REST = "(ignore)"

DATA_FILE_MIN_COVERAGE = 0.5  # share of recordings that must have a file kind

CHANNEL_MIN_COVERAGE = 0.5  # share of audio files that are channel siblings

CHANNEL_SAMPLE_GROUPS = 3  # groups whose headers are read to tell channels from takes

LAYOUT_TOML_KEY = "import"

CORPUS_TOML_KEY = "corpus"

# Files that describe the corpus as a whole (TalkBank's `0metadata.cdc`)
CORPUS_DESCRIPTION_SUFFIXES = (".cdc",)

LAYOUT_VERSION = 1

TIMIT_DEFAULT_SAMPLE_RATE = 16000

# a text table of intervals fits its audio file if it ends within this factor of its length
TIER_TABLE_DURATION_SLACK = 1.1

TABLE_MAX_HEADER_LINES = 20  # lines to look through for where a table's data begins
