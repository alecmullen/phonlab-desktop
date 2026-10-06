from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui.document.document_view import DocumentView
from ui.document.state.audio_channel_state import AudioChannelState, peak_dbfs


class AudioInfoDialog(QDialog):
    """Read-only summary of the current document's native (raw) audio."""

    def __init__(self, doc: DocumentView, tab_name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Audio Info"))

        raw = doc.view_model.primary_channel()
        if raw is None:
            raw = AudioChannelState()
        raw_duration = len(raw.x) / raw.fs if raw.fs else 0.0

        form = QFormLayout()
        form.addRow(self.tr("Name:"), QLabel(tab_name))
        form.addRow(self.tr("Sample rate:"), QLabel(self.tr("{} Hz").format(raw.fs)))
        form.addRow(
            self.tr("Duration:"), QLabel(self.tr("{:.3f} s").format(raw_duration))
        )
        stereo = doc.view_model.stereo_channels()
        if stereo is None:
            self._add_level_rows(
                form,
                raw,
                self.tr("Min / max amplitude:"),
                self.tr("Peak level:"),
            )
        else:
            left, right = (stereo.channels[idx] for idx in sorted(stereo.channels))
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
            QLabel(self.tr("{:.4g} / {:.4g}").format(min(channel.x), max(channel.x))),
        )
        form.addRow(
            peak_title, QLabel(self.tr("{:.2f} dBFS").format(peak_dbfs(channel.x)))
        )

    @staticmethod
    def show_info(doc: DocumentView, tab_name: str, parent: QWidget | None = None):
        dlg = AudioInfoDialog(doc, tab_name, parent)
        dlg.exec()
