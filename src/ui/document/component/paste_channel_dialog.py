from PyQt6.QtWidgets import QDialog, QMessageBox, QWidget


class PasteChannelDialog(QDialog):
    """Asks which channel (left/right) should hold the real audio when a
    paste mixes mono and stereo audio - the other channel is filled with a
    quiet noise placeholder."""

    @staticmethod
    def get_channel(parent: QWidget | None, is_clip_stereo: bool) -> int | None:
        dlg = PasteChannelDialog(parent)
        return dlg._ask(is_clip_stereo)

    def _get_message(self, is_clip_stereo: bool) -> str:
        if is_clip_stereo:
            return self.tr(
                "This clip is stereo, but the destination is mono. Pasting "
                "will convert the document to stereo - which channel should "
                "the existing audio occupy? The new channel will be filled "
                "with a quiet noise placeholder."
            )
        else:
            return self.tr(
                "This clip is mono, but the destination is stereo. Which "
                "channel should the clip's audio occupy? The other channel "
                "will be filled with a quiet noise placeholder."
            )

    def _ask(self, is_clip_stereo: bool) -> int | None:
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(self.tr("Assign Channel"))
        msg_box.setText(self._get_message(is_clip_stereo))
        left_button = msg_box.addButton(
            self.tr("Left Channel"), QMessageBox.ButtonRole.AcceptRole
        )
        right_button = msg_box.addButton(
            self.tr("Right Channel"), QMessageBox.ButtonRole.AcceptRole
        )
        msg_box.addButton(QMessageBox.StandardButton.Cancel)
        msg_box.setDefaultButton(left_button)
        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == left_button:
            return 0
        if clicked == right_button:
            return 1
        return None
