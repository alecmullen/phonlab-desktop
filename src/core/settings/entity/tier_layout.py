from dataclasses import dataclass, field


@dataclass
class TierLayout:
    """How a project shows its annotation tiers, by tier name: the ones to hide, and
    the order, bottom to top, of the others. A tier named in neither is shown after
    the ordered ones"""

    hidden_tiers: list[str] = field(default_factory=list)
    tier_order: list[str] = field(default_factory=list)
