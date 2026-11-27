from pathlib import Path

import pytest

from phonlab_project.readers.read_annotation import read_annotation
from phonlab_project.readers.read_tiers import read_tiers

HEADER = (
    "@UTF8\n@PID:\t11312/a-1\n@Begin\n@Languages:\teng\n"
    "@Participants:\tINV Investigator, PAR Participant\n"
    "@ID:\teng|CORAAL|INV|||||Investigator|||\n"
    "@ID:\teng|CORAAL|PAR|||||Participant|||\n@Media:\ta, audio\n"
)

TWO_SPEAKERS = (
    HEADER
    + "*INV:\tokay how's it going ? \x151005_3285\x15\n"
    + "%mor:\tintj|okay adv|how~aux|be-Fin-Ind-Pres-S3 pron|it-Prs-Nom-S3 ?\n"
    + "*PAR:\t&-um fine , thanks . \x153569_5025\x15\n"
    + "%wor:\tfine \x153569_3800\x15 thanks \x154000_5025\x15 .\n"
    + "*INV:\tgood . \x155100_5600\x15\n"
    + "@End\n"
)


def write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "a.cha"
    path.write_text(text, encoding="utf-8", newline="")
    return str(path)


def test_each_speaker_has_a_tier_of_their_utterances_in_seconds(tmp_path: Path):
    tiers = read_tiers(write(tmp_path, TWO_SPEAKERS))

    assert [tier["name"] for tier in tiers] == ["INV", "PAR"]
    assert tiers[0]["labels"] == [
        (1.005, 3.285, "okay how's it going ?"),
        (5.1, 5.6, "good ."),
    ]
    assert tiers[1]["labels"] == [(3.569, 5.025, "&-um fine , thanks .")]


def test_a_chat_file_names_no_talkers_only_roles(tmp_path: Path):
    tiers = read_tiers(write(tmp_path, TWO_SPEAKERS))

    assert all("talker" not in tier for tier in tiers)


def test_dependent_tiers_are_not_read(tmp_path: Path):
    labels = [
        t for tier in read_tiers(write(tmp_path, TWO_SPEAKERS)) for t in tier["labels"]
    ]

    assert len(labels) == 3


def test_an_utterance_with_no_time_is_left_out(tmp_path: Path):
    text = (
        HEADER + "*PAR:\tyeah . \x15100_200\x15\n*INV:\toh man .\n*PAR:\tbye .\n@End\n"
    )
    tiers = read_tiers(write(tmp_path, text))

    assert [tier["name"] for tier in tiers] == ["PAR", "INV"]
    assert tiers[0]["labels"] == [(0.1, 0.2, "yeah .")]
    assert tiers[1]["labels"] == []


def test_overlap_between_one_speakers_utterances_is_split_in_the_middle(
    tmp_path: Path,
):
    text = (
        HEADER
        + "*PAR:\tone . \x151000_2000\x15\n"
        + "*PAR:\ttwo . \x151800_3000\x15\n"
        + "*PAR:\tthree . \x153000_4000\x15\n"
        + "@End\n"
    )
    labels = read_tiers(write(tmp_path, text))[0]["labels"]

    assert labels == [(1.0, 1.9, "one ."), (1.9, 3.0, "two ."), (3.0, 4.0, "three .")]


def test_speakers_overlapping_each_other_are_left_alone(tmp_path: Path):
    text = (
        HEADER
        + "*INV:\tone . \x151000_2000\x15\n"
        + "*PAR:\ttwo . \x151800_3000\x15\n"
        + "@End\n"
    )
    tiers = read_tiers(write(tmp_path, text))

    assert tiers[0]["labels"] == [(1.0, 2.0, "one .")]
    assert tiers[1]["labels"] == [(1.8, 3.0, "two .")]


def test_a_line_that_starts_with_a_tab_continues_the_utterance(tmp_path: Path):
    text = HEADER + "*PAR:\tfirst part\n\tsecond part . \x15100_900\x15\n@End\n"

    assert read_tiers(write(tmp_path, text))[0]["labels"] == [
        (0.1, 0.9, "first part second part .")
    ]


def test_windows_line_endings_are_read(tmp_path: Path):
    text = TWO_SPEAKERS.replace("\n", "\r\n")

    assert len(read_tiers(write(tmp_path, text))) == 2


def test_chat_codes_are_kept_in_the_text(tmp_path: Path):
    text = (
        HEADER + "*PAR:\t<when you> [//] &=tsks interviewi^iewing . \x15100_900\x15\n"
    )

    assert read_tiers(write(tmp_path, text))[0]["labels"][0][2] == (
        "<when you> [//] &=tsks interviewi^iewing ."
    )


def test_read_annotation_gives_the_labels_as_a_table(tmp_path: Path):
    file = tmp_path / "f_01.cha"
    file.write_text(TWO_SPEAKERS, encoding="utf-8")

    labels = read_annotation(file)

    assert list(labels.tier) == ["INV", "INV", "PAR"]
    assert labels.t1.tolist() == [1.005, 5.1, 3.569]


def test_a_file_that_is_not_chat_cannot_be_read(tmp_path: Path):
    path = tmp_path / "a.cha"
    path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")

    with pytest.raises(ValueError, match="CHAT"):
        read_tiers(str(path))
