from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui.document.state.audio_channel_state import AudioChannelState


class AudioInfoDialog(QDialog):
    """Read-only summary of the current document's native (raw) audio."""

    def __init__(
        self,
        primary_channel: AudioChannelState | None,
        origin_name: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Audio Info"))

        if primary_channel is None:
            primary_channel = AudioChannelState()
        raw_duration = (
            len(primary_channel.x) / primary_channel.fs if primary_channel.fs else 0.0
        )

        form = QFormLayout()
        form.addRow(self.tr("Name:"), QLabel(origin_name))
        form.addRow(
            self.tr("Sample rate:"), QLabel(self.tr("{} Hz").format(primary_channel.fs))
        )
        form.addRow(
            self.tr("Duration:"), QLabel(self.tr("{:.3f} s").format(raw_duration))
        )
        min_max_label = None
        if len(primary_channel.x) > 0:
            min_max_label = QLabel(
                self.tr("{:.4g} / {:.4g}").format(
                    min(primary_channel.x), max(primary_channel.x)
                )
            )
        form.addRow(self.tr("Min / max amplitude:"), min_max_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @staticmethod
    def show_info(
        primary_channel: AudioChannelState | None,
        origin_name: str,
        parent: QWidget | None = None,
    ):
        dlg = AudioInfoDialog(primary_channel, origin_name, parent)
        dlg.exec()
