import numpy as np
import sounddevice as sd
from PyQt6.QtCore import pyqtSignal, QThread

class AudioPlayer(QThread):
    """Dedicated thread for audio playback"""
    finished = pyqtSignal()
    
    def __init__(self, audio_data, sample_rate):
        super().__init__()
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.should_stop = False
        
    def run(self):
        try:
            if len(self.audio_data) < self.sample_rate * 1:  # Less than 1 second
                pad_length = int(0.1 * self.sample_rate)  # 100ms padding
                padded_audio = np.concatenate([self.audio_data, np.zeros(pad_length)])
            else:
                padded_audio = self.audio_data
            sd.play(padded_audio, self.sample_rate, blocking=False, latency='high')
            sd.wait()
            
            if not self.should_stop:
                self.finished.emit()
        except Exception as e:
            print(f"Audio playback error: {e}")
     
    def stop(self):
        self.should_stop = True
        try:
            sd.stop()
        except:
            pass