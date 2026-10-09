from dataclasses import dataclass

from ui.base.state import State
from ui.document.state.audio_channel_state import AudioState


@dataclass(frozen=True)
class EditCommandState(State):
    """A record of a single edit command, for undo/redo purposes."""

    type: str  # "cut" | "paste" | "replace"
    start_idx: int
    new_clip: AudioState
    # "replace" only: the samples that `new_clip` overwrote
    replaced_clip: AudioState | None = None
