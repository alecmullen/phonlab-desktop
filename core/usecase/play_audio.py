import numpy as np
import sounddevice as sd

from core.usecase.use_case import UseCase


class PlayAudio(UseCase):
    
    def __init__(self, audio_data, sample_rate):
        self.audio_data = audio_data
        self.sample_rate = sample_rate

    def invoke(self):
        try:
            if len(self.audio_data) < self.sample_rate * 1:  # Less than 1 second
                pad_length = int(0.1 * self.sample_rate)  # 100ms padding
                padded_audio = np.concatenate([self.audio_data, np.zeros(pad_length)])
            else:
                padded_audio = self.audio_data
            sd.play(padded_audio, self.sample_rate, blocking=True, latency='high', blocksize=self.sample_rate)
            
            return True
        except RuntimeError as e:
            print(f"Audio playback error: {e}")
