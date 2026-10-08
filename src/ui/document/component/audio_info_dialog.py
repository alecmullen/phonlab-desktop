import numpy as np
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui.document.state.audio_channel_state import (
    AudioChannelState,
    AudioState,
    peak_dbfs,
)


class AudioInfoDialog(QDialog):
    """Read-only summary of the current document's native (raw) audio."""

    def __init__(
        self,
        primary_channel: AudioChannelState | None,
        stereo_channels: AudioState | None,
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
        if stereo_channels is None:
            self._add_level_rows(
                form,
                primary_channel,
                self.tr("Min / max amplitude:"),
                self.tr("Peak level:"),
            )
        else:
            left, right = (
                stereo_channels.channels[idx]
                for idx in sorted(stereo_channels.channels)
            )
            self._add_level_rows(
                form,
                left,
                self.tr("Left min / max amplitude:"),
                self.tr("Left peak level:"),
            )
            self._add_level_rows(
                form,
                right,
                self.tr("Right min / max amplitude:"),
                self.tr("Right peak level:"),
            )

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _add_level_rows(
        self,
        form: QFormLayout,
        channel: AudioChannelState,
        min_max_title: str,
        peak_title: str,
    ):
        """Min / max amplitude and peak level rows; blank (no peak row) when
        the channel has no samples."""
        if len(channel.x) == 0:
            form.addRow(min_max_title, None)
            return
        form.addRow(
            min_max_title,
            QLabel(
                self.tr("{:.4g} / {:.4g}").format(np.min(channel.x), np.max(channel.x))
            ),
        )
        form.addRow(
            peak_title, QLabel(self.tr("{:.2f} dBFS").format(peak_dbfs(channel.x)))
        )

    @staticmethod
    def show_info(
        primary_channel: AudioChannelState | None,
        stereo_channels: AudioState | None,
        origin_name: str,
        parent: QWidget | None = None,
    ):
        dlg = AudioInfoDialog(primary_channel, stereo_channels, origin_name, parent)
        dlg.exec()
