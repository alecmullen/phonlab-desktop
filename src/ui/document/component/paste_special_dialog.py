from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
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
    reverse: bool = False
    new_channel: bool = True


class PasteSpecialDialog(QDialog):
    """Lets the user choose how to paste the clipboard clip: optionally
    reversed, and, when both the document and the clip are mono, into a
    brand-new channel (promoting the document to stereo), either by
    inserting silence into the original audio (which lengthens both
    channels together) or by placing the clip directly at the mark position
    without changing the original audio's own timeline. When a new channel
    isn't possible, or isn't ticked, the clip is pasted as an ordinary
    paste."""

    def __init__(
        self, parent: QWidget | None = None, new_channel_available: bool = True
    ):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Paste Special"))

        self.channel_group_box = QGroupBox(self.tr("Paste into a new channel"))
        self.channel_group_box.setCheckable(True)
        self.channel_group_box.setChecked(new_channel_available)
        channel_layout = QVBoxLayout(self.channel_group_box)
        self.channel_button_group = QButtonGroup(self)
        for idx in range(2):
            channel_radio = QRadioButton(self.tr("Channel {}").format(idx + 1))
            if idx == 1:
                channel_radio.setChecked(True)
            self.channel_button_group.addButton(channel_radio, id=idx)

            channel_layout.addWidget(channel_radio)

        self.silence_group_box = QGroupBox(self.tr("Silence"))
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
        silence_layout = QVBoxLayout(self.silence_group_box)
        silence_layout.addWidget(self.with_silence_radio)
        silence_layout.addWidget(self.without_silence_radio)

        self.channel_group_box.toggled.connect(self.silence_group_box.setEnabled)
        self.silence_group_box.setEnabled(new_channel_available)
        if not new_channel_available:
            # Needs a mono document and a mono clip.
            self.channel_group_box.setEnabled(False)
            self.channel_group_box.setToolTip(
                self.tr("Only available when the document and the clip are both mono")
            )

        self.reverse_check_box = QCheckBox(self.tr("Reverse the audio before pasting"))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.channel_group_box)
        layout.addWidget(self.silence_group_box)
        layout.addWidget(self.reverse_check_box)
        layout.addWidget(buttons)

    def choice(self) -> PasteSpecialChoice:
        buttons = self.channel_button_group.buttons()
        new_channel_idx = next(
            (idx for idx, btn in enumerate(buttons) if btn.isChecked()), 1
        )
        return PasteSpecialChoice(
            new_channel_idx=new_channel_idx,
            insert_silence=self.with_silence_radio.isChecked(),
            reverse=self.reverse_check_box.isChecked(),
            new_channel=self.channel_group_box.isChecked(),
        )

    @staticmethod
    def get_choice(
        parent: QWidget | None = None, new_channel_available: bool = True
    ) -> PasteSpecialChoice | None:
        dlg = PasteSpecialDialog(parent, new_channel_available)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.choice()
        return None
