from PyQt6.QtCore import QObject
from PyQt6.QtGui import QAction


class ContextMenuHintAction(QAction):
    """A menu action with an optional right-aligned hint, e.g. "Set Mark  Click".

    Uses a plain QAction (hint after a tab, which Qt lays out in the
    shortcut column) rather than a QWidgetAction with a custom widget,
    because custom-widget rows intermittently failed to paint their text.
    """

    def __init__(
        self,
        action_text: str,
        hint_text: str | None = None,
        parent: QObject | None = None,
    ):
        text = action_text if hint_text is None else f"{action_text}\t{hint_text}"
        super().__init__(text, parent)
