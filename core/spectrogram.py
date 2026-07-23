import warnings

import librosa
import numpy as np
from PyQt6.QtCore import QMutexLocker, QThread, pyqtSignal


class SpectrogramWorker(QThread):
    """Worker thread for computing spectrogram asynchronously"""
    progress = pyqtSignal(int, float, np.ndarray)  # percent, max_time_computed, freqs
    finished = pyqtSignal(np.ndarray, np.ndarray, np.ndarray)  # ts, freqs, Sxx
    error = pyqtSignal(str)
    
    def __init__(self, y, fs, window_size=0.008, step_size=0.002, order = 12, chunk_duration=5.0):
        super().__init__()
        self.y = y
        self.fs = fs
        self.window_size = window_size
        self.step_size = step_size
        self.order = order
        self.chunk_duration = chunk_duration
        self.should_stop = False
        
        # For mmap storage
        self.use_mmap = False
        self.mmap_file = None
        self.ts_file = None
        self.Sxx_mmap = None
        self.ts_mmap = None
        self.n_freqs = None
        self.frames_computed = 0  # Track how many frames have been computed
        self.mmap_lock = None  # For thread-safe access
        self.partial_ts = None
        self.partial_Sxx = None

    def compute_sgram(self, audio, fs, w=0.008, s=0.001, order=12):

        n_fft = int(np.power(2,order))
        hop_length = int(s * fs)
        win_length = int(w * fs)

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='nfft=.* is too large')
            D = librosa.stft(audio, n_fft=n_fft, win_length=win_length,
                         hop_length=hop_length, window='hann')
        Sxx = 20*np.log10(np.abs(D) ** 2)

        freqs = librosa.fft_frequencies(sr=fs, n_fft=n_fft)
        times = librosa.frames_to_time(np.arange(Sxx.shape[1]), sr=fs, hop_length=hop_length)
        
        return times, freqs, Sxx
        
    def run(self):
        self.setPriority(QThread.Priority.LowPriority)

        try:
            total_duration = len(self.y) / self.fs
            
            # For very long files (>5 minutes), use memory-mapped file
            self.use_mmap = total_duration > 300 # 5 minutes
            
            if self.use_mmap:
                self.compute_with_mmap()
            else:
                self.compute_incremental()
                
        except RuntimeError as e:
            import traceback
            self.error.emit(f"{e!s}\n{traceback.format_exc()}")
    
    def get_window(self, start_time, end_time):
        """Extract a time window from the computed spectrogram (thread-safe)"""
        if self.use_mmap:
            if self.ts_mmap is None or self.Sxx_mmap is None:
                return None, None
        
            # Thread-safe access
            if self.mmap_lock:
                QMutexLocker(self.mmap_lock)
        
            try:
                # Find frame indices for the requested window
                # Only search in computed frames
                computed_ts = self.ts_mmap[:self.frames_computed]
                
                if len(computed_ts) == 0:
                    return None, None
            
                # Check if requested window is within computed range
                if start_time > computed_ts[-1]:
                    return None, None
            
                sfr = np.abs(computed_ts - start_time).argmin()
            
                if end_time > computed_ts[-1]:
                    efr = self.frames_computed - 1
                else:
                    efr = np.abs(computed_ts - end_time).argmin()
                
                if sfr >= efr:
                    efr = min(sfr + 1, self.frames_computed - 1)
            
                # Extract the window
                ts_window = np.array(self.ts_mmap[sfr:efr+1])
                Sxx_window = np.array(self.Sxx_mmap[:, sfr:efr+1])
            
                return ts_window, Sxx_window
            
            except RuntimeError as e:
                print(f"Error extracting window: {e}")
                return None, None
        else:
            # Non-mmap mode - extract from partial data
            if self.partial_ts is None or self.partial_Sxx is None:
                return None, None
        
            try:
                # Check if requested window is within computed range
                if start_time > self.partial_ts[-1]:
                    return None, None
            
                sfr = np.abs(self.partial_ts - start_time).argmin()
            
                if end_time > self.partial_ts[-1]:
                    efr = len(self.partial_ts) - 1
                else:
                    efr = np.abs(self.partial_ts - end_time).argmin()
            
                if sfr >= efr:
                    efr = min(sfr + 1, len(self.partial_ts) - 1)
            
                # Extract the window
                ts_window = self.partial_ts[sfr:efr+1]
                Sxx_window = self.partial_Sxx[:, sfr:efr+1]
            
                return ts_window, Sxx_window
            
            except ValueError as e:
                print(f"Error extracting window from partial data: {e}")
                return None, None

    def compute_incremental(self):
        """Compute spectrogram incrementally for moderate-length files"""
        chunk_samples = int(self.chunk_duration * self.fs)
        num_chunks = int(np.ceil(len(self.y) / chunk_samples))
        
        all_freqs = None
        all_ts = []
        all_Sxx = []
        
        for i in range(num_chunks):
            if self.should_stop:
                return
            
            start_idx = i * chunk_samples
            end_idx = min((i + 1) * chunk_samples, len(self.y))
            
            chunk = self.y[start_idx:end_idx]
            
            # Compute spectrogram for this chunk
            ts, freqs, Sxx = self.compute_sgram(chunk, self.fs, self.window_size,
                                                self.step_size, self.order)
            
            # Adjust time stamps to absolute time
            ts = ts + (start_idx / self.fs)
            
            if all_freqs is None:
                all_freqs = freqs
            
            all_ts.append(ts)
            all_Sxx.append(Sxx)
            
            # Emit progress with partial results
            percent = int(((i + 1) / num_chunks) * 100)
            
            # Concatenate what we have so far
            combined_ts = np.concatenate(all_ts)
            combined_Sxx = np.concatenate(all_Sxx, axis=1)
            
            max_time = combined_ts[-1]

            self.partial_ts = combined_ts
            self.partial_Sxx = combined_Sxx
            self.progress.emit(percent, max_time, all_freqs)
        
        # Emit final result
        final_ts = np.concatenate(all_ts)
        final_Sxx = np.concatenate(all_Sxx, axis=1)
        self.finished.emit(final_ts, all_freqs, final_Sxx)
    
    def compute_with_mmap(self):
        """Compute spectrogram with memory-mapped file for very long audio"""
        import os
        import tempfile

        from PyQt6.QtCore import QMutex
        
        # Initialize mutex for thread-safe access
        self.mmap_lock = QMutex()
        
        # Do a test computation to get exact parameters
        test_samples = min(len(self.y), int(self.fs * 1.0))
        test_ts, freqs, test_Sxx = self.compute_sgram(
            self.y[:test_samples], self.fs, self.window_size, self.step_size, self.order)
        
        self.n_freqs = test_Sxx.shape[0]
        
        # Calculate frames per second
        frames_per_sec = len(test_ts) / (test_samples / self.fs)
        
        # Estimate total frames needed (with buffer)
        estimated_frames = int(frames_per_sec * (len(self.y) / self.fs) * 1.2)
        
        # Create memory-mapped files
        temp_dir = tempfile.gettempdir()
        self.mmap_file = os.path.join(temp_dir, f'spectrogram_{id(self)}.dat')
        self.ts_file = os.path.join(temp_dir, f'spectrogram_ts_{id(self)}.dat')
        
        try:
            # Create the memory-mapped arrays
            self.Sxx_mmap = np.memmap(self.mmap_file, dtype='float32', mode='w+', 
                                     shape=(self.n_freqs, estimated_frames))
            self.ts_mmap = np.memmap(self.ts_file, dtype='float64', mode='w+',
                                    shape=(estimated_frames,))
        except MemoryError as e:
            self.error.emit(f"Failed to create memory-mapped file: {e}")
            return
        
        chunk_samples = int(self.chunk_duration * self.fs)
        num_chunks = int(np.ceil(len(self.y) / chunk_samples))
        
        frame_offset = 0
        
        for i in range(num_chunks):
            if self.should_stop:
                self.cleanup_mmap()
                return
            
            start_idx = i * chunk_samples
            end_idx = min((i + 1) * chunk_samples, len(self.y))
            
            chunk = self.y[start_idx:end_idx]
            
            # Compute spectrogram for this chunk
            ts, chunk_freqs, Sxx = self.compute_sgram(chunk, self.fs,self.window_size,
                                                      self.step_size, self.order)
            
            # Verify frequency dimensions match
            if chunk_freqs.shape[0] != self.n_freqs:
                self.error.emit(f"Frequency dimension mismatch: expected {self.n_freqs}, got {chunk_freqs.shape[0]}")
                self.cleanup_mmap()
                return
            
            # Adjust time stamps
            ts = ts + (start_idx / self.fs)
            
            # Write to memory-mapped file
            n_frames_chunk = Sxx.shape[1]
            
            if frame_offset + n_frames_chunk > estimated_frames:
                self.error.emit("Ran out of space in mmap")
                self.cleanup_mmap()
                return
            
            # Thread-safe write
            self.mmap_lock.lock()
            try:
                self.Sxx_mmap[:, frame_offset:frame_offset + n_frames_chunk] = Sxx
                self.ts_mmap[frame_offset:frame_offset + n_frames_chunk] = ts
                self.frames_computed = frame_offset + n_frames_chunk
            finally:
                self.mmap_lock.unlock()
            
            frame_offset += n_frames_chunk
            
            # Emit progress
            percent = int(((i + 1) / num_chunks) * 100)
            max_time = ts[-1]
            self.progress.emit(percent, max_time, freqs)
        
        # Final result - convert to regular arrays and clean up mmap
        final_ts = np.array(self.ts_mmap[:frame_offset])
        Sxx_final = np.array(self.Sxx_mmap[:, :frame_offset])
        
        # Clean up mmap after copying data
        self.cleanup_mmap()
        
        # Emit final result
        self.finished.emit(final_ts, freqs, Sxx_final)
    
    def cleanup_mmap(self):
        """Clean up memory-mapped files"""
        import os
        
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
    
    def stop(self):
        self.should_stop = True
        self.cleanup_mmap()
