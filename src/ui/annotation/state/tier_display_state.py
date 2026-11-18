from collections.abc import Collection, Mapping
from dataclasses import dataclass

from ui.annotation.state.annotation_state import tier_order_key
from ui.base.state import State

HIDDEN_POSITION = 0


@dataclass(frozen=True)
class TierDisplayState(State):
    """How a tier is displayed: `position` 1 is the bottom row of the plot, 2 the
    next one up and so on. `HIDDEN_POSITION` leaves the tier out"""

    name: str
    position: int = HIDDEN_POSITION
    n_labels: int = 0  # how many labels the tier has in the current file


def tier_display_from(
    names: list[str],
    hidden_tiers: Collection[str],
    tier_order: Collection[str],
    label_counts: Mapping[str, int] | None = None,
) -> list[TierDisplayState]:
    """Every tier in the order it is shown, bottom to top, then the hidden ones, with
    the number of labels each has (in `label_counts`; none if it is not named)"""
    counts = label_counts or {}
    order_key = tier_order_key(tier_order)
    shown = sorted((name for name in names if name not in hidden_tiers), key=order_key)
    return [
        *(
            TierDisplayState(name, position, counts.get(name, 0))
            for position, name in enumerate(shown, 1)
        ),
        *(
            TierDisplayState(name, HIDDEN_POSITION, counts.get(name, 0))
            for name in names
            if name in hidden_tiers
        ),
    ]


def listed_as_plotted(tiers: list[TierDisplayState]) -> list[TierDisplayState]:
    """`tiers` as a list shows them: the tier at the top of the plot first, and the
    hidden ones last"""
    shown = [tier for tier in tiers if tier.position != HIDDEN_POSITION]
    hidden = [tier for tier in tiers if tier.position == HIDDEN_POSITION]
    return [*reversed(shown), *hidden]


def hidden_and_order_from(
    tiers: list[TierDisplayState],
) -> tuple[list[str], list[str]]:
    """The names of the hidden tiers, and of the others in the order to show them. Tiers
    given the same position keep the order they are listed in"""
    hidden = [tier.name for tier in tiers if tier.position == HIDDEN_POSITION]
    shown = sorted(
        (tier for tier in tiers if tier.position != HIDDEN_POSITION),
        key=lambda tier: tier.position,
    )
    return hidden, [tier.name for tier in shown]
