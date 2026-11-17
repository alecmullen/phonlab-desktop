from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from core.read_tiers.read_tiers import read_tiers

BUCKEYE_WORDS = """header line
#
  0.5000 121 <SIL>
  1.2000 121 hello; hh ax l ow; hh l ow; UH
  2.0000 121 big dog; b ih g d ao g; b ih g d ao g; NN
"""

BUCKEYE_PHONES = """header line
#
  0.5000 122 SIL
  0.7000 122 hh; 3
  1.2000 122 l+1
"""


def test_buckeye_words_and_phones_become_two_tiers(tmp_path: Path):
    (tmp_path / "s0101a.words").write_text(BUCKEYE_WORDS)
    (tmp_path / "s0101a.phones").write_text(BUCKEYE_PHONES)

    word, phone = read_tiers(str(tmp_path / "s0101a.words"))

    assert word["name"] == "word"
    assert word["labels"] == [
        (0.0, 0.5, "<SIL>"),
        (0.5, 1.2, "hello"),
        (1.2, 2.0, "big_dog"),
    ]
    assert phone["name"] == "phone"
    assert phone["labels"] == [(0.0, 0.5, "SIL"), (0.5, 0.7, "hh"), (0.7, 1.2, "l")]


def test_buckeye_words_without_phones_give_only_a_word_tier(tmp_path: Path):
    (tmp_path / "a.words").write_text(BUCKEYE_WORDS)

    tiers = read_tiers(str(tmp_path / "a.words"))

    assert [tier["name"] for tier in tiers] == ["word"]


def test_buckeye_upper_case_extensions_find_their_companion(tmp_path: Path):
    (tmp_path / "A.WORDS").write_text(BUCKEYE_WORDS)
    (tmp_path / "A.PHONES").write_text(BUCKEYE_PHONES)

    tiers = read_tiers(str(tmp_path / "A.WORDS"))

    assert [tier["name"] for tier in tiers] == ["word", "phone"]


def test_buckeye_file_without_header_end_is_rejected(tmp_path: Path):
    (tmp_path / "a.words").write_text("no header marker here\n")

    with pytest.raises(ValueError):
        read_tiers(str(tmp_path / "a.words"))


def test_timit_times_in_samples_are_converted_with_the_default_rate(tmp_path: Path):
    (tmp_path / "sa1.wrd").write_text("0 8000 she\n8000 24000 had\n")
    (tmp_path / "sa1.phn").write_text("0 4000 sh\n4000 8000 iy\n")

    word, phone = read_tiers(str(tmp_path / "sa1.wrd"))

    assert word["labels"] == [(0.0, 0.5, "she"), (0.5, 1.5, "had")]
    assert phone["labels"] == [(0.0, 0.25, "sh"), (0.25, 0.5, "iy")]


def test_timit_uses_the_sample_rate_of_the_sound_file(tmp_path: Path):
    sf.write(tmp_path / "sa1.wav", np.zeros(100), 8000)
    (tmp_path / "sa1.wrd").write_text("0 8000 she\n")

    [word] = read_tiers(str(tmp_path / "sa1.wrd"))

    assert word["labels"] == [(0.0, 1.0, "she")]


def test_timit_upper_case_extensions(tmp_path: Path):
    (tmp_path / "SA1.WRD").write_text("0 16000 she\n")
    (tmp_path / "SA1.PHN").write_text("0 16000 sh\n")

    tiers = read_tiers(str(tmp_path / "SA1.WRD"))

    assert [tier["name"] for tier in tiers] == ["word", "phone"]


def test_timit_bad_line_is_rejected(tmp_path: Path):
    (tmp_path / "a.wrd").write_text("zero ten she\n")

    with pytest.raises(ValueError):
        read_tiers(str(tmp_path / "a.wrd"))


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_phonetic_symbols_are_read_in_either_encoding(tmp_path: Path, encoding: str):
    text = (SIMPLE_TEXTGRID_SYMBOLS).replace("PHONES", "ʃɪŋ̩θ")
    (tmp_path / "a.TextGrid").write_bytes(text.encode(encoding))

    [tier] = read_tiers(str(tmp_path / "a.TextGrid"))

    assert [label[2] for label in tier["labels"]] == ["ʃɪŋ̩θ", "ʃɪŋ̩θ"]


SIMPLE_TEXTGRID_SYMBOLS = """File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1.0
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "phones"
        xmin = 0
        xmax = 1.0
        intervals: size = 2
        intervals [1]:
            xmin = 0
            xmax = 0.5
            text = "PHONES"
        intervals [2]:
            xmin = 0.5
            xmax = 1.0
            text = "PHONES"
"""
