from dataclasses import dataclass, field


@dataclass
class TierLayout:
    """How a project shows its annotation tiers, by tier name: the ones to hide, and
    the order, bottom to top, of the others. A tier named in neither is shown after
    the ordered ones. Also the font family of each tier's labels; a tier with none
    uses the default font"""

    hidden_tiers: list[str] = field(default_factory=list)
    tier_order: list[str] = field(default_factory=list)
    tier_fonts: dict[str, str] = field(default_factory=dict)
