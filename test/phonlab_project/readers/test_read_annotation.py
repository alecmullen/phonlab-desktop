from pathlib import Path

import pandas as pd
import pytest
from support.textgrid import word_and_phone_textgrid

from phonlab_project import ProjectError, read_annotation

SRT = (
    "1\n00:00:00,000 --> 00:00:01,000\nAnn: Hi there\n\n"
    "2\n00:00:01,000 --> 00:00:02,000\nBob: Hello\n\n"
    "3\n00:00:02,000 --> 00:00:03,000\nBye\n"
)

POINT_TIER = """File type = "ooTextFile"
Object class = "TextGrid"

xmin = 0
xmax = 1
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "TextTier"
        name = "tones"
        xmin = 0
        xmax = 1
        points: size = 2
        points [1]:
            number = 0.25
            mark = "H"
        points [2]:
            number = 0.75
            mark = "L"
"""


@pytest.fixture
def textgrid(tmp_path: Path) -> Path:
    file = tmp_path / "s1.TextGrid"
    file.write_text(word_and_phone_textgrid())
    return file


def test_the_labels_of_every_tier_are_rows_in_the_order_of_the_file(textgrid: Path):
    labels = read_annotation(textgrid)

    assert list(labels.columns) == ["tier", "talker", "t1", "t2", "label"]
    assert labels.tier.tolist() == ["word"] * 2 + ["phone"] * 4
    assert labels.label.tolist() == ["hi", "yo", "h", "i", "y", "o"]
    assert labels.t1.tolist()[:2] == [0.0, 0.5]
    assert labels.t2.tolist()[:2] == [0.5, 1.0]
    assert labels.t1.dtype == float and labels.t2.dtype == float


def test_a_textgrid_says_nothing_of_who_made_a_tier(textgrid: Path):
    assert read_annotation(textgrid).talker.isna().all()


def test_the_extension_can_be_in_any_case(tmp_path: Path):
    file = tmp_path / "s1.textgrid"
    file.write_text(word_and_phone_textgrid())

    assert len(read_annotation(file)) == 6


def test_a_path_may_be_text(textgrid: Path):
    assert len(read_annotation(str(textgrid))) == 6


def test_subtitles_are_labels_of_the_tier_of_their_talker_who_is_named_when_it_changes(
    tmp_path: Path,
):
    file = tmp_path / "s1.srt"
    file.write_text(SRT)

    labels = read_annotation(file)

    # "Bye" names no talker, so it is the last one named: Bob
    assert labels.tier.tolist() == ["Ann", "Bob", "Bob"]
    assert labels.talker.tolist() == ["Ann", "Bob", "Bob"]
    assert labels.label.tolist() == ["Hi there", "Hello", "Bye"]


def test_a_point_ends_where_it_begins(tmp_path: Path):
    file = tmp_path / "tones.TextGrid"
    file.write_text(POINT_TIER)

    labels = read_annotation(file)

    assert labels.t1.tolist() == [0.25, 0.75]
    assert labels.t2.tolist() == [0.25, 0.75]


def test_tiers_can_be_chosen_by_name(textgrid: Path):
    assert read_annotation(textgrid, "word").label.tolist() == ["hi", "yo"]
    both = read_annotation(textgrid, ["phone", "word"])
    assert both.tier.unique().tolist() == ["word", "phone"]  # file order


def test_a_tier_the_file_lacks_raises_with_the_ones_it_has(textgrid: Path):
    with pytest.raises(ProjectError, match=r"no tier \['syllable'\]; it has \['word'"):
        read_annotation(textgrid, "syllable")


def test_a_file_of_another_kind_is_not_read(tmp_path: Path):
    file = tmp_path / "notes.txt"
    file.write_text("hello")

    with pytest.raises(ProjectError, match="notes.txt"):
        read_annotation(file)


def test_a_file_that_is_not_there_raises(tmp_path: Path):
    with pytest.raises(OSError):
        read_annotation(tmp_path / "nowhere.srt")


def test_a_file_without_labels_gives_an_empty_table_of_the_same_columns(
    tmp_path: Path,
):
    file = tmp_path / "empty.srt"
    file.write_text("")

    labels = read_annotation(file)

    assert labels.empty
    assert list(labels.columns) == ["tier", "talker", "t1", "t2", "label"]
    assert isinstance(labels, pd.DataFrame)
