from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class FormantTrack:
    """Formant measurements of an audio clip. `sec` is the time of each frame
    in seconds from the start of the clip, in increasing order; `formants` has
    shape (frames, 4), one column each for F1-F4 in Hz. `order` is the LPC
    order the frames were measured with, or 0 for a method without one."""

    sec: np.ndarray = field(default_factory=lambda: np.zeros(0))
    formants: np.ndarray = field(default_factory=lambda: np.zeros((0, 4)))
    order: int = 0

    def merged_with(self, other: "FormantTrack") -> "FormantTrack":
        """This track and `other`, whose frames may fall anywhere among
        these (pieces of a file are measured out of order)."""
        sec = np.concatenate([self.sec, other.sec])
        formants = np.concatenate([self.formants, other.formants])
        order = np.argsort(sec, kind="stable")
        return FormantTrack(sec[order], formants[order], self.order or other.order)

    def between(self, start: float, end: float) -> "FormantTrack":
        """The frames from time `start` to time `end`, inclusive"""
        first = np.searchsorted(self.sec, start, side="left")
        last = np.searchsorted(self.sec, end, side="right")
        return FormantTrack(self.sec[first:last], self.formants[first:last], self.order)
