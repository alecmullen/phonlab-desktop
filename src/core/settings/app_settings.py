from dataclasses import dataclass, field


@dataclass
class AppSettings:
    """Process-wide user preferences. Currently mutated directly (no
    settings UI yet); a future Settings menu should just read/write the
    fields on the shared `settings` instance below."""

    cut_and_paste_at_zero_crossings: bool = False

    # Names of the plots every document shows, updated as the user toggles
    # plots on and off. Kept for the session only; a project can store its own
    # via `SaveDisplayPlan`.
    display_plan: list[str] = field(default_factory=lambda: ["waveform"])

    # Names of the annotation tiers left out of every document. A tier not named
    # here is shown, including ones that are added later. Kept for the session only;
    # a project can store its own.
    hidden_tiers: list[str] = field(default_factory=list)

    # Names of the annotation tiers in the order they are shown, top to bottom.
    # Tiers not named here come after them. Kept for the session only; a project
    # can store its own.
    tier_order: list[str] = field(default_factory=list)

    enable_annotation = True


settings = AppSettings()
