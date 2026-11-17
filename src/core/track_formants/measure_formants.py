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
    """Track the formants of `x` with the chosen method, every 10 ms. The
    result has a `sec` column (the time of each frame, from the start of `x`)
    and the columns F1-F4 in Hz. Every method does its own resampling and
    preemphasis, so `x` is the raw audio."""
    preemph = options.preemphasis
    with FORMANT_LOCK:
        match options.method:
            case FormantMethod.IFC:
                df = phon.IFC_formants(x, fs, preemph=preemph, speaker=options.speaker)
            case FormantMethod.LPC:
                df = phon.LPC_formants(x, fs, preemph=preemph, order=options.order)
            case FormantMethod.RLPC:
                df, _ = phon.RLPC_formants(
                    x,
                    fs,
                    tf=options.top_frequency,
                    preemph=preemph,
                    order=options.order,
                )
            case FormantMethod.TVLP:
                df = phon.TVLP_formants(
                    x,
                    fs,
                    tf=options.top_frequency,
                    order=options.order,
                    preemph=preemph,
                    f0median=options.median_f0,
                )
            case FormantMethod.DPPT:
                df = phon.DPPT_formants(x, fs, preemph=preemph, deltaF=options.delta_f)
    return df[["sec", *FORMANT_COLUMNS]]


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
    with FORMANT_LOCK:
        prepped, prepped_fs = phon.prep_audio(
            x,
            fs,
            target_fs=target_fs,
            preemph=options.preemphasis,
            scale=True,
            fix_polarity=fix_polarity,
        )
        order, _ = phon.choose_order(prepped, prepped_fs)
    return replace(options, order=int(order))
