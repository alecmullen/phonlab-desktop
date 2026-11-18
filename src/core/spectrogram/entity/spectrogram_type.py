from enum import StrEnum


class SpectrogramType(StrEnum):
    """The kinds of spectrogram phonlab can compute, named as it names them.

    The Bark type is left out: its frequency axis is not in Hz. (The mel type
    is in, with its rows' frequencies converted to Hz.)"""

    FFT = "fft"
    MULTITAPER = "multitaper"
    CEPSTRAL = "cepstral"
    LPC = "lpc"
    MEL = "mel"
