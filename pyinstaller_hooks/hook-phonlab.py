from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("phonlab")

hiddenimports = [
    "phonlab",
    "phonlab.acoustic.sgram_",
    "phonlab.acoustic.tidypraat",
    "phonlab.acoustic.track_formants_",
    "phonlab.utils.prep_audio_",
    "phonlab.utils.signal",
    "phonlab.utils.textgrid",
]
