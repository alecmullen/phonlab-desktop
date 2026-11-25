from pathlib import Path

from support.audio_files import textgrid_with_tiers

from core.project_layout.suggest_talker_names import (
    SuggestTalkerNames,
    talker_names_from_tiers,
)


def test_talker_before_the_kind_of_tier():
    assert talker_names_from_tiers(
        ["Ann - words", "Ann - phones", "Bob - words", "Bob - phones"]
    ) == ["Ann", "Bob"]


def test_talker_after_the_kind_of_tier():
    assert talker_names_from_tiers(["words - Ann", "words - Bob"]) == ["Ann", "Bob"]


def test_tiers_named_for_talkers():
    assert talker_names_from_tiers(["JW", "KJ"]) == ["JW", "KJ"]


def test_tiers_named_for_their_content_suggest_nothing():
    assert talker_names_from_tiers(["words", "phones", "notes"]) == []


def test_ambiguous_separated_names_suggest_nothing():
    assert talker_names_from_tiers(["a - b", "c - d"]) == []


def test_names_come_from_the_tiers_of_an_annotation_file(tmp_path: Path):
    (tmp_path / "a.TextGrid").write_text(
        textgrid_with_tiers(["Ann - words", "Bob - words"])
    )

    assert SuggestTalkerNames()(str(tmp_path), "a.TextGrid") == ["Ann", "Bob"]


def test_an_unreadable_file_suggests_nothing(tmp_path: Path):
    (tmp_path / "a.TextGrid").write_text("not a textgrid")

    assert SuggestTalkerNames()(str(tmp_path), "a.TextGrid") == []
    assert SuggestTalkerNames()(str(tmp_path), "missing.TextGrid") == []


def test_the_tier_for_subtitles_with_no_talker_is_not_a_talker_name():
    assert talker_names_from_tiers(["Camille", "subtitles"]) == ["Camille"]
