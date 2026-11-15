from enum import StrEnum


class SpectrogramType(StrEnum):
    """The kinds of spectrogram phonlab can compute, named as it names them.

    The mel and Bark types are left out: their frequency axes are not in Hz."""

    FFT = "fft"
    MULTITAPER = "multitaper"
    CEPSTRAL = "cepstral"
    LPC = "lpc"
