from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QWidget,
    QWidgetAction,
)


class ContextMenuHint(QWidget):
    def __init__(
        self,
        action_text: str,
        hint_text: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        # Hover highlighting is done with a stylesheet (rather than
        # manually toggling autoFillBackground/backgroundRole from
        # enterEvent/leaveEvent) so Qt's own style engine owns the repaint.
        self.setStyleSheet(
            "ContextMenuHint:hover { background-color: palette(highlight); }"
            "ContextMenuHint:hover QLabel { color: palette(highlighted-text); }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 4, 18, 4)

        self.label_title = QLabel(action_text)
        layout.addWidget(self.label_title)

        if hint_text is not None:
            self.label_hint = QLabel(hint_text)
            self.label_hint.setStyleSheet("color: gray;")

            self.spacer = QSpacerItem(
                10, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
            layout.addSpacerItem(self.spacer)
            layout.addWidget(self.label_hint)


class ContextMenuHintAction(QWidgetAction):
    def __init__(
        self,
        action_text: str,
        hint_text: str | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.action_text = action_text
        self.hint_text = hint_text

    def createWidget(self, parent: QWidget | None = None) -> QWidget:
        return ContextMenuHint(self.action_text, self.hint_text, parent)
