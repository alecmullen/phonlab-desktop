import os
import tempfile
import weakref

import numpy as np
import phonlab as phon

from core.base.use_case import UseCase
from core.spectrogram.entity.spectrogram_mmap import SpectrogramMmap


class ComputeSpectrogramMmap(UseCase[SpectrogramMmap]):
    def __call__(
        self,
        x: np.ndarray,
        fs: int,
        window_size: float = 0.008,
        step_size: float = 0.001,
        order: int = 9,
        chunk_duration: int = 300,
    ):
        sxx_mmap = t_mmap = None
        mmap_file = ts_file = ""
        try:
            n_freqs, frames_per_sec = self.estimate_resolution(
                x, fs, window_size, step_size, order
            )

            # Estimate total frames needed (with buffer)
            estimated_frames = int(frames_per_sec * (len(x) / fs) * 1.2)

            # Every computation needs files of its own: this use case is shared by
            # all documents, and a file recreated or deleted by one computation
            # would pull the pages out from under another one still mapped to it
            # (a bus error, SIGBUS, when it next touches them)
            temp_dir = tempfile.gettempdir()
            mmap_file = self.new_temp_file(temp_dir, "spectrogram_")
            ts_file = self.new_temp_file(temp_dir, "spectrogram_ts_")

            sxx_mmap, t_mmap = self.init_mmap(
                mmap_file, ts_file, n_freqs, estimated_frames
            )

            # The spectrogram outlives this generator, which ends normally once all
            # chunks are computed. Remove the files when it is no longer referenced
            remove_file_when_released(sxx_mmap, mmap_file)
            remove_file_when_released(t_mmap, ts_file)

            chunk_samples = int(chunk_duration * fs)
            frame_offset = 0

            for i in range(0, len(x), chunk_samples):
                start = i
                end = min(i + chunk_samples, len(x))

                chunk = x[start:end]
                ts, _, sxx = phon.compute_sgram(
                    chunk, fs, window_size, step_size, order
                )
                ts = ts + (start / fs)

                if frame_offset > estimated_frames:
                    raise RuntimeError("Ran out of space in mmap")

                n_frames_chunk = sxx.shape[1]

                sxx_mmap[:, frame_offset : frame_offset + n_frames_chunk] = sxx
                t_mmap[frame_offset : frame_offset + n_frames_chunk] = ts
                frame_offset += n_frames_chunk

                yield SpectrogramMmap(
                    t_mmap=t_mmap,
                    sxx_mmap=sxx_mmap,
                    frames_per_sec=frames_per_sec,
                    frames_computed=frame_offset,
                    samples_computed=end,
                )
        except GeneratorExit:
            self.cleanup_mmaps(sxx_mmap, t_mmap, mmap_file, ts_file)
        except Exception as e:
            self.cleanup_mmaps(sxx_mmap, t_mmap, mmap_file, ts_file)
            raise RuntimeError(f"Error during spectrogram computation: {e}") from e

    def new_temp_file(self, temp_dir: str, prefix: str) -> str:
        """Create an empty file with a name no other computation will get"""
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=".dat", dir=temp_dir)
        os.close(fd)
        return path

    def estimate_resolution(
        self,
        x: np.ndarray,
        fs: int,
        window_size: float = 0.008,
        step_size: float = 0.001,
        order: int = 9,
    ) -> tuple[int, float]:
        test_samples = min(len(x), fs)

        test_ts: np.ndarray
        test_sxx: np.ndarray
        test_ts, _, test_sxx = phon.compute_sgram(
            x[:test_samples], fs, window_size, step_size, order
        )

        n_freqs = test_sxx.shape[0]

        frames_per_sec = len(test_ts) / (test_samples / fs)

        return n_freqs, frames_per_sec

    def init_mmap(
        self, mmap_file: str, ts_file: str, n_freqs: int, estimated_frames: int
    ) -> tuple[np.memmap, np.memmap]:
        try:
            sxx_mmap = np.memmap(
                mmap_file,
                dtype="float32",
                mode="w+",
                shape=(n_freqs, estimated_frames),
            )
            ts_mmap = np.memmap(
                ts_file, dtype="float64", mode="w+", shape=(estimated_frames,)
            )
        except MemoryError as e:
            raise MemoryError(f"Failed to create memory-mapped file: {e}") from e

        return sxx_mmap, ts_mmap

    def cleanup_mmaps(
        self,
        sxx_mmap: np.memmap | None,
        t_mmap: np.memmap | None,
        mmap_file: str,
        ts_file: str,
    ):
        if sxx_mmap is not None:
            del sxx_mmap

        if t_mmap is not None:
            del t_mmap

        if mmap_file and os.path.exists(mmap_file):
            os.remove(mmap_file)

        if ts_file and os.path.exists(ts_file):
            os.remove(ts_file)


def remove_file_when_released(array: np.memmap, path: str):
    """Delete `path` once `array`, which is mapped to it, has been garbage collected
    (or when the program exits)"""
    weakref.finalize(array, remove_quietly, path)


def remove_quietly(path: str):
    try:
        os.remove(path)
    except OSError:
        # Already removed, or (on Windows) still mapped by something else
        pass
