from dataclasses import dataclass, field

from res.constants import LABEL_HEIGHT_RATIO
from ui.base.state import State


@dataclass(frozen=True)
class AnnotationLabelState(State):
    s_node: int = 0
    e_node: int = 0
    label: str = ""

    is_visible: bool = False
    pos: tuple[float, float] = field(default_factory=tuple)
    size: tuple[float, float] = field(default_factory=tuple)


def update_label_state(
    label: AnnotationLabelState,
    win_start: float,
    win_end: float,
    start: float,
    end: float,
    tier: int,
) -> AnnotationLabelState:
    if end <= win_start or start >= win_end:
        return AnnotationLabelState(label.s_node, label.e_node, label.label, False)

    x_s = max(win_start, start)
    x_e = min(win_end, end)

    center_x = (x_e - x_s) / 2 + x_s
    center_y = tier + 0.5
    width = x_e - x_s

    return AnnotationLabelState(
        label.s_node,
        label.e_node,
        label.label,
        True,
        (center_x, center_y),
        (width, LABEL_HEIGHT_RATIO),
    )
