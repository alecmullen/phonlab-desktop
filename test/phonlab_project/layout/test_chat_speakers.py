from pathlib import Path

from phonlab_project.layout.chat_speakers import name_chat_speakers
from phonlab_project.recording import Recording


def chat(tmp_path: Path, name: str, speakers: list[str]) -> str:
    lines = ["@UTF8", "@Begin"]
    lines += [f"*{code}:\thi . \x15100_200\x15" for code in speakers]
    (tmp_path / name).write_text("\n".join([*lines, "@End", ""]), encoding="utf-8")
    return name


def test_the_participant_is_the_talker_of_the_layout_and_others_are_numbered(
    tmp_path: Path,
):
    recordings = [
        Recording(
            "a",
            annotation_file=chat(tmp_path, "a.cha", ["INV", "PAR"]),
            talkers=["ann"],
        ),
        Recording(
            "b",
            annotation_file=chat(tmp_path, "b.cha", ["PAR", "INV", "UID"]),
            talkers=["bob"],
        ),
        Recording(
            "c", annotation_file=chat(tmp_path, "c.cha", ["INV", "PAR"]), talkers=["cy"]
        ),
    ]

    a, b, c = name_chat_speakers(recordings, str(tmp_path))

    assert a.tier_talkers == {"INV": "INV1", "PAR": "ann"}
    assert b.tier_talkers == {"PAR": "bob", "INV": "INV2", "UID": "UID1"}
    assert c.tier_talkers == {"INV": "INV3", "PAR": "cy"}
    assert a.talkers == ["ann", "INV1"]
    assert b.talkers == ["bob", "INV2", "UID1"]


def test_a_participant_the_layout_does_not_name_is_numbered_too(tmp_path: Path):
    [a] = name_chat_speakers(
        [Recording("a", annotation_file=chat(tmp_path, "a.cha", ["PAR"]))],
        str(tmp_path),
    )

    assert a.tier_talkers == {"PAR": "PAR1"}


def test_a_code_that_ends_in_a_digit_is_joined_to_its_number_by_an_underscore(
    tmp_path: Path,
):
    [a] = name_chat_speakers(
        [
            Recording(
                "a", annotation_file=chat(tmp_path, "a.cha", ["PAR2"]), talkers=["x"]
            )
        ],
        str(tmp_path),
    )

    assert a.tier_talkers == {"PAR2": "PAR2_1"}


def test_recordings_with_other_annotations_or_unreadable_ones_are_left_alone(
    tmp_path: Path,
):
    recordings = [
        Recording("a", annotation_file="a.TextGrid", talkers=["ann"]),
        Recording("b", talkers=["bob"]),
        Recording("c", annotation_file="missing.cha", talkers=["cy"]),
    ]

    assert name_chat_speakers(recordings, str(tmp_path)) == recordings
