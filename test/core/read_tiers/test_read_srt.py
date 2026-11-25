from pathlib import Path

import pytest

from core.read_tiers.read_tiers import read_tiers

TWO_TALKERS = """1
00:00:01,000 --> 00:00:02,500
Camille: Okay, this is
the start

2
00:00:02,500 --> 00:00:04,000
and it goes on.

3
00:00:04,250 --> 00:00:05,000
S24-003: Yeah.

4
00:00:05,500 --> 00:00:06,000
Camille: Cool.
"""


def write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "a.srt"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_each_talker_has_a_tier_of_their_subtitles(tmp_path: Path):
    tiers = read_tiers(write(tmp_path, TWO_TALKERS))

    assert [tier["name"] for tier in tiers] == ["Camille", "S24-003"]
    assert [tier["talker"] for tier in tiers] == ["Camille", "S24-003"]
    assert tiers[0]["labels"] == [
        (1.0, 2.5, "Okay, this is the start"),
        (2.5, 4.0, "and it goes on."),
        (5.5, 6.0, "Cool."),
    ]
    assert tiers[1]["labels"] == [(4.25, 5.0, "Yeah.")]


def test_a_subtitle_with_no_name_is_by_the_talker_before_it(tmp_path: Path):
    tiers = read_tiers(write(tmp_path, TWO_TALKERS))

    assert "and it goes on." in [label[2] for label in tiers[0]["labels"]]


def test_subtitles_before_any_talker_is_named_have_a_tier_with_no_talker(
    tmp_path: Path,
):
    tiers = read_tiers(
        write(
            tmp_path,
            "1\n00:00:00,000 --> 00:00:01,000\nHello\n\n"
            "2\n00:00:01,000 --> 00:00:02,000\nAnn: Hi\n",
        )
    )

    assert [tier["name"] for tier in tiers] == ["subtitles", "Ann"]
    assert "talker" not in tiers[0]
    assert tiers[0]["labels"] == [(0.0, 1.0, "Hello")]


def test_a_file_that_names_no_talker_is_one_tier(tmp_path: Path):
    tiers = read_tiers(
        write(tmp_path, "1\n00:00:00,000 --> 00:00:01,000\nSee the time 10:30 now\n")
    )

    assert tiers == [
        {"name": "subtitles", "labels": [(0.0, 1.0, "See the time 10:30 now")]}
    ]


def test_a_long_start_before_a_colon_is_not_a_talker(tmp_path: Path):
    long_start = "x" * 41
    tiers = read_tiers(
        write(tmp_path, f"1\n00:00:00,000 --> 00:00:01,000\n{long_start}: text\n")
    )

    assert [tier["name"] for tier in tiers] == ["subtitles"]


def test_a_subtitle_with_only_a_talker_has_no_label(tmp_path: Path):
    tiers = read_tiers(
        write(
            tmp_path,
            "1\n00:00:00,000 --> 00:00:01,000\nAnn:\n\n"
            "2\n00:00:01,000 --> 00:00:02,000\nhello\n",
        )
    )

    assert tiers == [{"name": "Ann", "labels": [(1.0, 2.0, "hello")], "talker": "Ann"}]


def test_a_file_that_is_not_srt_cannot_be_read(tmp_path: Path):
    with pytest.raises(ValueError, match="Cannot read"):
        read_tiers(write(tmp_path, "1\nnot a time\nhello\n"))


def test_only_the_first_colon_separates_the_talker_from_the_utterance(tmp_path: Path):
    tiers = read_tiers(
        write(
            tmp_path,
            "1\n00:00:00,000 --> 00:00:01,000\nAnn: she said: wait: now\n\n"
            "2\n00:00:01,000 --> 00:00:02,000\nat 10:30: and 11:45\n",
        )
    )

    assert tiers == [
        {
            "name": "Ann",
            "talker": "Ann",
            "labels": [
                (0.0, 1.0, "she said: wait: now"),
                (1.0, 2.0, "at 10:30: and 11:45"),
            ],
        }
    ]


def test_a_colon_in_an_utterance_with_no_talker_is_kept(tmp_path: Path):
    tiers = read_tiers(
        write(
            tmp_path,
            "1\n00:00:00,000 --> 00:00:01,000\nAnn: hello\n\n"
            "2\n00:00:01,000 --> 00:00:02,000\nthe time was 10:30\n",
        )
    )

    assert [label[2] for label in tiers[0]["labels"]] == [
        "hello",
        "the time was 10:30",
    ]
