import numpy as np

from core.track_formants.entity.formant_track import FormantTrack
from ui.spectrogram.state.formant_track_state import to_formant_track_state


def test_to_formant_track_state_shifts_times_by_offset():
    formants = np.arange(8, dtype=float).reshape(2, 4)
    track = FormantTrack(np.array([0.01, 0.02]), formants)

    state = to_formant_track_state(track, offset=2.5)

    np.testing.assert_allclose(state.sec, [2.51, 2.52])
    np.testing.assert_array_equal(state.formants, formants)
