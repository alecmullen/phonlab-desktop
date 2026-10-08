from dataclasses import dataclass
from enum import StrEnum

from res.constants import DEFAULT_FILTER_ORDER


class FilterType(StrEnum):
    BANDPASS = "bandpass"
    LOWPASS = "lowpass"
    HIGHPASS = "highpass"


@dataclass(frozen=True)
class FilterSpec:
    """Filter parameters. `low` is the lower band edge (bandpass) or the
    cutoff (highpass); `high` is the upper band edge (bandpass) or the cutoff
    (lowpass)."""

    type: FilterType
    low: float | None = None
    high: float | None = None
    order: int = DEFAULT_FILTER_ORDER

    def bounds(self) -> float | list[float]:
        if self.type == FilterType.BANDPASS:
            if self.low is None or self.high is None:
                raise ValueError("Bandpass needs low and high edges")
            return [self.low, self.high]
        cutoff = self.high if self.type == FilterType.LOWPASS else self.low
        if cutoff is None:
            raise ValueError("Filter needs a cutoff")
        return cutoff
