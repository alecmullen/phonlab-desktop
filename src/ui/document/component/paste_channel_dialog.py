from PyQt6.QtWidgets import QDialog, QMessageBox, QWidget


class PasteChannelDialog(QDialog):
    """Asks which channel (left/right) should hold the real audio when a
    paste mixes mono and stereo audio - the other channel is filled with a
    quiet noise placeholder."""

    @staticmethod
    def get_channel(parent: QWidget | None, message: str) -> int | None:
        dlg = PasteChannelDialog(parent)
        return dlg._ask(message)

    def _ask(self, message: str) -> int | None:
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(self.tr("Assign Channel"))
        msg_box.setText(message)
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
