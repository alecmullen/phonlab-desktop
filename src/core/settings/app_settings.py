from dataclasses import dataclass, field


@dataclass
class AppSettings:
    """Process-wide user preferences."""

    cut_and_paste_at_zero_crossings: bool = False

    # Names of the plots every document shows
    display_plan: list[str] = field(default_factory=lambda: ["waveform"])

    enable_annotation = True


settings = AppSettings()
