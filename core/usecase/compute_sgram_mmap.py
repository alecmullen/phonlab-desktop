import os
import tempfile

from core.usecase.use_case import UseCase

import numpy as np
import phonlab as phon


class ComputeSpectrogramMmap(UseCase):

    def __init__(self, x, fs, window_size=0.008, step_size=0.002, order=9, chunk_duration=300):
        self.x = x
        self.fs = fs
        self.window_size = window_size
        self.step_size = step_size
        self.order = order
        self.chunk_duration=chunk_duration

    def invoke(self) -> tuple[np.memmap, np.memmap, float]:
        test_samples = min(len(self.x), int(self.fs * 1.0))
        test_ts, _, test_Sxx = phon.compute_sgram(self.x[:test_samples], self.fs, self.window_size, self.step_size, self.order)
        
        n_freqs = test_Sxx.shape[0]
        
        # Calculate frames per second
        frames_per_sec = len(test_ts) / (test_samples / self.fs)
        
        # Estimate total frames needed (with buffer)
        estimated_frames = int(frames_per_sec * (len(self.x) / self.fs) * 1.2)
        
        # Create memory-mapped files
        temp_dir = tempfile.gettempdir()
        mmap_file = os.path.join(temp_dir, f'spectrogram_{id(self)}.dat')
        ts_file = os.path.join(temp_dir, f'spectrogram_ts_{id(self)}.dat')
        
        try:
            # Create the memory-mapped arrays
            Sxx_mmap = np.memmap(mmap_file, dtype='float32', mode='w+', 
                                        shape=(n_freqs, estimated_frames))
            ts_mmap = np.memmap(ts_file, dtype='float64', mode='w+',
                                    shape=(estimated_frames,))
        except MemoryError as e:
            raise MemoryError(f"Failed to create memory-mapped file: {e}") from e
        
        chunk_samples = int(self.chunk_duration * self.fs)
        num_chunks = int(np.ceil(len(self.x) / chunk_samples))
        
        frame_offset = 0
        
        for i in range(num_chunks):
            
            start_idx = i * chunk_samples
            end_idx = min((i + 1) * chunk_samples, len(self.x))
            
            chunk = self.x[start_idx:end_idx]
            
            # Compute spectrogram for this chunk
            ts, _, Sxx = phon.compute_sgram(chunk, self.fs,self.window_size,
                                                        self.step_size, self.order)
            
            # Adjust time stamps
            ts = ts + (start_idx / self.fs)
            
            # Write to memory-mapped file
            n_frames_chunk = Sxx.shape[1]
            
            if frame_offset + n_frames_chunk > estimated_frames:
                self.error.emit("Ran out of space in mmap")
                self.cleanup_mmap()
                return
            
            Sxx_mmap[:, frame_offset:frame_offset + n_frames_chunk] = Sxx
            ts_mmap[frame_offset:frame_offset + n_frames_chunk] = ts
            frames_computed = frame_offset + n_frames_chunk
            frame_offset += n_frames_chunk

        return Sxx_mmap, ts_mmap, frames_per_sec, frames_computed