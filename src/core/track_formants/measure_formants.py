from dataclasses import replace

import numpy as np
import pandas as pd
import phonlab as phon

from core.track_formants.entity.formant_method import FormantMethod
from core.track_formants.entity.formant_options import FormantOptions
from core.track_formants.formant_lock import FORMANT_LOCK
from res.constants import FORMANT_LPC_SAMPLE_RATE

FORMANT_COLUMNS = ["F1", "F2", "F3", "F4"]
ORDER_METHODS = (FormantMethod.LPC, FormantMethod.RLPC, FormantMethod.TVLP)


def measure_formants(x: np.ndarray, fs: int, options: FormantOptions) -> pd.DataFrame:
    """Track the formants of `x` with the chosen method. The result has a
    `sec` column (the time of each frame, from the start of `x`) and the
    columns F1-F4 in Hz. Every method does its own resampling and
    preemphasis, so `x` is the raw audio."""
    df = _track(x, fs, options)
    if options.voiced_only:
        df = _without_voiceless_frames(df, x, fs, options.voicing_threshold)
    return df[["sec", *FORMANT_COLUMNS]]


def _track(x: np.ndarray, fs: int, options: FormantOptions) -> pd.DataFrame:
    preemph = options.preemphasis
    step, length = options.step, options.length
    with FORMANT_LOCK:
        match options.method:
            case FormantMethod.IFC:
                return phon.IFC_formants(
                    x, fs, preemph=preemph, speaker=options.speaker
                )
            case FormantMethod.LPC:
                return phon.LPC_formants(
                    x,
                    fs,
                    preemph=preemph,
                    order=options.order,
                    step=step,
                    length=length,
                )
            case FormantMethod.RLPC:
                df, _ = phon.RLPC_formants(
                    x,
                    fs,
                    tf=options.top_frequency,
                    preemph=preemph,
                    order=options.order,
                    step=step,
                    length=length,
                )
                return df
            case FormantMethod.TVLP:
                return phon.TVLP_formants(
                    x,
                    fs,
                    tf=options.top_frequency,
                    order=options.order,
                    preemph=preemph,
                    f0median=options.median_f0,
                    step=step,
                    length=length,
                )
            case FormantMethod.DPPT:
                return phon.DPPT_formants(
                    x,
                    fs,
                    preemph=preemph,
                    deltaF=options.delta_f,
                    step=step,
                    length=length,
                )


def _without_voiceless_frames(
    df: pd.DataFrame, x: np.ndarray, fs: int, threshold: float
) -> pd.DataFrame:
    """`df` with the formants of frames that phon.VAD() finds voiceless set
    to NaN"""
    vad = phon.VAD(x, fs, threshold=threshold)
    df = phon.align_timeseries(df, vad, ts="sec", other_columns=["voiced"])
    df.loc[~df["voiced"].astype(bool), FORMANT_COLUMNS] = np.nan
    return df


def with_chosen_order(
    x: np.ndarray, fs: int, options: FormantOptions
) -> FormantOptions:
    """The options with the LPC order fixed. When the order is automatic,
    phonlab picks it from the loudest frame of the audio it is given, so
    pieces of a file measured separately could get different orders and their
    formants would jump at the seams. Choosing once, from `x`, avoids that."""
    if options.method not in ORDER_METHODS or options.order > 0:
        return options

    # the audio as the method would prepare it
    if options.method == FormantMethod.LPC:
        target_fs, fix_polarity = FORMANT_LPC_SAMPLE_RATE, False
    else:
        target_fs, fix_polarity = options.top_frequency * 2, True
    # LPC_formants and RLPC_formants choose with their frame length; TVLP's
    # frames are longer than choose_order() is meant for, so it uses the default
    frame_args = () if options.method == FormantMethod.TVLP else (options.length,)
    with FORMANT_LOCK:
        prepped, prepped_fs = phon.prep_audio(
            x,
            fs,
            target_fs=target_fs,
            preemph=options.preemphasis,
            scale=True,
            fix_polarity=fix_polarity,
        )
        order, _ = phon.choose_order(prepped, prepped_fs, *frame_args)
    return replace(options, order=int(order))
