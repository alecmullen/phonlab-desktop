import numpy as np
from scipy.signal import spectrogram, windows


def compute_sgram(x,fs,w,s=0.001,order=13):
    """Compute a spectrogram from input waveform array of samples.
    
    Parameters
    ==========
    x : ndarray
        array of audio samples
    fs : integer
        The sampling frequency of the audio samples in `x` 
    w : float
        Length in seconds of the analysis window.  For an effective filter bandwidth of 300 Hz use w = 0.008, and for an effective filter bandwidth of 45 Hz use w = 0.04.
    s : float, default=0.001
        The time (in seconds) between adjacent spectra in the spectrogram. 
    order : integer, default = 13
        This parameter determines the number of points in the FFT analysis that produces the spectrogram.  The number of points will be a power of 2 (2**order) and should be larder than the number of points in the analysis window (which is w*fs).

    Returns
    ======= 
    t : ndarray
        Array of segment times.
    f : ndarray
        Array of sample frequencies.
    Sxx : ndarray
        Spectrogram of the audio. By default, the last axis of Sxx corresponds to the segment times.
        It is the magnitude spectrum on the decibel scale, so 20 * log10(Sxx) of the spectrogram
        returned by scipy.signal.spectrogram.


    """
    step = s  # step size between spectral slices (sec)
     
    # set up parameters for signal.spectrogram()
    noverlap = int((w-step)*fs) # skip forward by step between each frame
    nperseg = int(w*fs)         # number of samples per waveform window
    nfft = np.power(2,order)    # number of points in the fft
    window = windows.blackmanharris(nperseg)

    f,ts,Sxx = spectrogram(x,fs=fs,noverlap = noverlap, window=window, nperseg = nperseg, 
                              nfft = nfft, scaling='spectrum', mode = 'magnitude')
    Sxx = 10 * np.log10(Sxx)  # put spectrum on decibel scale

    return (ts, f, Sxx)