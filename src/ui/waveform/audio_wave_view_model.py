from ui.base.view_model import ViewModel
from ui.waveform.state.audio_wave_range_state import AudioWaveScaleState
from ui.waveform.state.audio_wave_state import AudioWaveState


class AudioWaveViewModel(ViewModel):
    def __init__(self):
        super().__init__()
        self.audio_wave_scale_state = AudioWaveScaleState()
        self.audio_wave_state = AudioWaveState()

    def update_wave_y_range(self, delta: float):
        if delta > 0:
            y_scale = 1.05 * self.audio_wave_scale_state.y_scale
        else:
            y_scale = 0.95 * self.audio_wave_scale_state.y_scale

        y_scale = max(0.1, min(10.0, y_scale))

        min_x, max_x = self.audio_wave_state.max_x, self.audio_wave_state.min_x
        y_max = max(abs(min_x), abs(max_x))
        scaled_max = y_max / y_scale

        self.audio_wave_scale_state = AudioWaveScaleState(y_scale, scaled_max)
        self.state_changed.emit(self.audio_wave_scale_state)

    def set_wave_state(self, state: AudioWaveState):
        self.audio_wave_state = state
        self.state_changed.emit(state)
