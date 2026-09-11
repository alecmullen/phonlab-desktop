from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QEnterEvent, QPalette
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

    def enterEvent(self, event: QEnterEvent | None):
        self.highlight(True)

    def leaveEvent(self, a0: QEvent | None):
        self.highlight(False)

    def highlight(self, value: bool):
        if value:
            self.setBackgroundRole(QPalette.ColorRole.Highlight)
        else:
            self.setBackgroundRole(QPalette.ColorRole.Window)

        self.setAutoFillBackground(value)


class ContextMenuHintAction(QWidgetAction):
    def __init__(
        self,
        action_text: str,
        hint_text: str | None = None,
        widget_parent: QWidget | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.action_text = action_text
        self.hint_text = hint_text

        self.widget_parent = widget_parent

    def createWidget(self, parent: QWidget | None = None) -> QWidget:
        # if self.widget_parent is not None:
        #     parent = self.widget_parent
        return ContextMenuHint(self.action_text, self.hint_text, parent)
