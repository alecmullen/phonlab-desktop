import os
import tempfile

import numpy as np
import phonlab as phon

from core.usecase.use_case import UseCase


class ComputeSpectrogramMmap(UseCase[tuple[np.memmap, np.memmap, float]]):

    def __init__(self, x: np.ndarray, fs: int, window_size:float=0.008, step_size:float=0.002, order:int=9, chunk_duration:int=300):
        self.x = x
        self.fs = fs
        self.window_size = window_size
        self.step_size = step_size
        self.order = order
        self.chunk_duration=chunk_duration

    def invoke(self):
        try:
            Sxx_mmap, ts_mmap, frames_per_sec, estimated_frames = self.init_mmap()
            
            chunk_samples = int(self.chunk_duration * self.fs)            
            frame_offset = 0
            
            for i in range(0, len(self.x), chunk_samples):
                start = i
                end = min(i + chunk_samples, len(self.x))
                
                chunk = self.x[start:end]
                ts, _, sxx = phon.compute_sgram(chunk, self.fs,self.window_size, self.step_size, self.order)
                ts = ts + (start / self.fs)

                if frame_offset > estimated_frames:
                    self.error.emit("Ran out of space in mmap")
                    self.stop()
                    return

                n_frames_chunk = sxx.shape[1]

                Sxx_mmap[:, frame_offset:frame_offset + n_frames_chunk] = sxx
                ts_mmap[frame_offset:frame_offset + n_frames_chunk] = ts
                frame_offset += n_frames_chunk

                yield Sxx_mmap, ts_mmap, frames_per_sec, frame_offset, end
        except Exception as e:
            self.error.emit(f"Error during spectrogram computation: {e}")
            self.stop()
            raise

    def init_mmap(self):
        test_samples = min(len(self.x), self.fs)
        test_ts, _, test_Sxx = phon.compute_sgram(self.x[:test_samples], self.fs, self.window_size, self.step_size, self.order)
        
        n_freqs = test_Sxx.shape[0]
        
        frames_per_sec = len(test_ts) / (test_samples / self.fs)
        
        # Estimate total frames needed (with buffer)
        estimated_frames = int(frames_per_sec * (len(self.x) / self.fs) * 1.2)
        
        temp_dir = tempfile.gettempdir()
        mmap_file = os.path.join(temp_dir, f'spectrogram_{id(self)}.dat')
        ts_file = os.path.join(temp_dir, f'spectrogram_ts_{id(self)}.dat')
        
        try:
            Sxx_mmap = np.memmap(mmap_file, dtype='float32', mode='w+', 
                                        shape=(n_freqs, estimated_frames))
            ts_mmap = np.memmap(ts_file, dtype='float64', mode='w+',
                                    shape=(estimated_frames,))
        except MemoryError as e:
            raise MemoryError(f"Failed to create memory-mapped file: {e}") from e

        return Sxx_mmap, ts_mmap, frames_per_sec, estimated_frames

    def stop(self):
        if self.Sxx_mmap is not None:
            del self.Sxx_mmap
            self.Sxx_mmap = None
        
        if self.ts_mmap is not None:
            del self.ts_mmap
            self.ts_mmap = None
        
        if self.mmap_file and os.path.exists(self.mmap_file):
            os.remove(self.mmap_file)
            self.mmap_file = None
        
        if self.ts_file and os.path.exists(self.ts_file):
            os.remove(self.ts_file)
            self.ts_file = None
