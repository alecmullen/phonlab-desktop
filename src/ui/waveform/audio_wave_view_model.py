from PyQt6.QtCore import pyqtSlot

from ui.base.view_model import ViewModel
from ui.waveform.state.audio_wave_action import (
    AudioFilterAction,
    AudioInfoAction,
    AudioResampleAction,
    AudioReverseAction,
    AudioRevertToOriginalAction,
    AudioScaleAction,
)
from ui.waveform.state.audio_wave_range_state import AudioWaveScaleState
from ui.waveform.state.audio_wave_state import AudioWaveState
from ui.waveform.state.channel_active_state import ChannelActiveState
from ui.waveform.state.delete_channel_state import DeleteChannelState


class AudioWaveViewModel(ViewModel):
    def __init__(self, channel_idx: int = 0):
        super().__init__()
        self.channel_idx: int = channel_idx
        self.audio_wave_scale_state = AudioWaveScaleState()
        self.audio_wave_state = AudioWaveState()
        self.channel_active_state = ChannelActiveState()

    def update_wave_y_range(self, delta: float):
        if delta < 0:
            y_scale = 1.05 * self.audio_wave_scale_state.y_scale
        else:
            y_scale = 0.95 * self.audio_wave_scale_state.y_scale

        y_scale = max(1.0, min(10.0, y_scale))

        min_x, max_x = self.audio_wave_state.max_x, self.audio_wave_state.min_x
        y_max = max(abs(min_x), abs(max_x))
        scaled_max = y_max / y_scale

        self.audio_wave_scale_state = AudioWaveScaleState(y_scale, scaled_max)
        self.state_changed.emit(self.audio_wave_scale_state)

    def set_wave_state(self, state: AudioWaveState):
        self.audio_wave_state = state
        self.state_changed.emit(state)

    @pyqtSlot()
    def scale_audio(self):
        self.state_changed.emit(AudioScaleAction())

    @pyqtSlot()
    def filter_audio(self):
        self.state_changed.emit(AudioFilterAction())

    @pyqtSlot()
    def resample_audio(self):
        self.state_changed.emit(AudioResampleAction())

    @pyqtSlot()
    def open_audio_info(self):
        self.state_changed.emit(AudioInfoAction())

    @pyqtSlot()
    def revert_to_original(self):
        self.state_changed.emit(AudioRevertToOriginalAction())

    @pyqtSlot()
    def reverse_audio(self):
        self.state_changed.emit(AudioReverseAction())

    def delete_channel(self):
        self.state_changed.emit(DeleteChannelState(self.channel_idx))

    def toggle_active(self, is_active: bool):
        self.channel_active_state = ChannelActiveState(self.channel_idx, is_active)
        self.state_changed.emit(self.channel_active_state)
