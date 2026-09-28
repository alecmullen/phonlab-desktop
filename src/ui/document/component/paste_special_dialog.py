from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


@dataclass
class PasteSpecialChoice:
    new_channel_idx: int
    insert_silence: bool


class PasteSpecialDialog(QDialog):
    """Lets the user choose a "paste special" action for the current
    clipboard clip. The only action today is "New Channel" - paste a mono
    clip into a brand-new channel of a mono document, promoting it to
    stereo, either by inserting silence into the original audio (which
    lengthens both channels together) or by placing the clip directly at
    the mark position without changing the original audio's own timeline.
    More actions may be added here later."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Paste Special"))

        channel_group_box = QGroupBox(self.tr("New Channel"))
        self.channel1_radio = QRadioButton(self.tr("Channel 1"))
        self.channel2_radio = QRadioButton(self.tr("Channel 2"))
        self.channel2_radio.setChecked(True)
        self.channel_button_group = QButtonGroup(self)
        self.channel_button_group.addButton(self.channel1_radio)
        self.channel_button_group.addButton(self.channel2_radio)
        channel_layout = QVBoxLayout(channel_group_box)
        channel_layout.addWidget(self.channel1_radio)
        channel_layout.addWidget(self.channel2_radio)

        silence_group_box = QGroupBox(self.tr("Silence"))
        self.with_silence_radio = QRadioButton(
            self.tr("Insert silence into original audio")
        )
        self.without_silence_radio = QRadioButton(
            self.tr("Don't insert silence into original audio")
        )
        self.with_silence_radio.setChecked(True)
        self.silence_button_group = QButtonGroup(self)
        self.silence_button_group.addButton(self.with_silence_radio)
        self.silence_button_group.addButton(self.without_silence_radio)
        silence_layout = QVBoxLayout(silence_group_box)
        silence_layout.addWidget(self.with_silence_radio)
        silence_layout.addWidget(self.without_silence_radio)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(channel_group_box)
        layout.addWidget(silence_group_box)
        layout.addWidget(buttons)

    def choice(self) -> PasteSpecialChoice:
        return PasteSpecialChoice(
            new_channel_idx=0 if self.channel1_radio.isChecked() else 1,
            insert_silence=self.with_silence_radio.isChecked(),
        )

    @staticmethod
    def get_choice(parent: QWidget | None = None) -> PasteSpecialChoice | None:
        dlg = PasteSpecialDialog(parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.choice()
        return None
