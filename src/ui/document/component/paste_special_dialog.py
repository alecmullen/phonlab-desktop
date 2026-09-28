from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class PasteSpecialDialog(QDialog):
    """Lets the user choose a "paste special" action for the current
    clipboard clip. The only action today is "New Channel" - paste a mono
    clip into a brand-new channel of a mono document, promoting it to
    stereo. More actions may be added here later."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Paste Special"))

        group_box = QGroupBox(self.tr("New Channel"))
        self.channel1_radio = QRadioButton(self.tr("Channel 1"))
        self.channel2_radio = QRadioButton(self.tr("Channel 2"))
        self.channel2_radio.setChecked(True)
        self.channel_group = QButtonGroup(self)
        self.channel_group.addButton(self.channel1_radio)
        self.channel_group.addButton(self.channel2_radio)
        group_layout = QVBoxLayout(group_box)
        group_layout.addWidget(self.channel1_radio)
        group_layout.addWidget(self.channel2_radio)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(group_box)
        layout.addWidget(buttons)

    def new_channel_index(self) -> int:
        return 0 if self.channel1_radio.isChecked() else 1

    @staticmethod
    def get_new_channel_index(parent: QWidget | None = None) -> int | None:
        dlg = PasteSpecialDialog(parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.new_channel_index()
        return None
