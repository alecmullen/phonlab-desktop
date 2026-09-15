from dataclasses import dataclass


@dataclass
class AppSettings:
    """Process-wide user preferences. Currently mutated directly (no
    settings UI yet); a future Settings menu should just read/write the
    fields on the shared `settings` instance below."""

    cut_and_paste_at_zero_crossings: bool = True

    enable_annotation = True


settings = AppSettings()
