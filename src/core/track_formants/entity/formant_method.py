from enum import StrEnum


class FormantMethod(StrEnum):
    """The formant tracking functions of phonlab. Values are the keys of the
    per-method defaults in `res.constants`."""

    IFC = "ifc"
    LPC = "lpc"
    RLPC = "rlpc"
    TVLP = "tvlp"
    DPPT = "dppt"
