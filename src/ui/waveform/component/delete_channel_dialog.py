from PyQt6.QtWidgets import QDialog, QMessageBox, QWidget


class DeleteChannelDialog(QDialog):
    """Confirms deleting a channel from a stereo document before
    converting it to mono - the operation is not undoable, so the user
    gets one chance to back out."""

    @staticmethod
    def confirm(parent: QWidget | None) -> bool:
        dlg = DeleteChannelDialog(parent)
        return dlg._ask()

    def _ask(self) -> bool:
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(self.tr("Delete Channel"))
        msg_box.setText(
            self.tr(
                "Delete this channel and convert the file to mono? "
                "This cannot be undone."
            )
        )
        delete_button = msg_box.addButton(
            self.tr("Delete"), QMessageBox.ButtonRole.DestructiveRole
        )
        msg_box.addButton(QMessageBox.StandardButton.Cancel)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        msg_box.exec()

        return msg_box.clickedButton() == delete_button
