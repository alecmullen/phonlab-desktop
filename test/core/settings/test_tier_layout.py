import tomllib
from pathlib import Path

import pytest

from core.settings.entity.tier_layout import TierLayout
from core.settings.load_tier_layout import LoadTierLayout
from core.settings.save_display_plan import SaveDisplayPlan
from core.settings.save_tier_layout import SaveTierLayout


def read(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def test_load_returns_an_empty_layout_without_a_project_file(tmp_path: Path):
    assert LoadTierLayout()(str(tmp_path)) == TierLayout()


def test_load_returns_an_empty_layout_when_project_has_none(tmp_path: Path):
    (tmp_path / "phonlab.toml").write_text("")

    assert LoadTierLayout()(str(tmp_path)) == TierLayout()


def test_save_writes_layout_to_project_file(tmp_path: Path):
    SaveTierLayout()(TierLayout(["phone"], ["word", "tone"]), str(tmp_path))

    assert read(tmp_path / "phonlab.toml") == {
        "display": {"hidden_tiers": ["phone"], "tier_order": ["word", "tone"]}
    }


def test_save_keeps_the_display_plan_and_other_contents(tmp_path: Path):
    (tmp_path / "phonlab.toml").write_text('name = "demo"\n')
    SaveDisplayPlan()(["waveform"], str(tmp_path))

    SaveTierLayout()(TierLayout(["phone"], []), str(tmp_path))

    assert read(tmp_path / "phonlab.toml") == {
        "name": "demo",
        "display": {"plan": ["waveform"], "hidden_tiers": ["phone"]},
    }


def test_save_leaves_out_empty_lists_and_removes_earlier_ones(tmp_path: Path):
    SaveTierLayout()(TierLayout(["phone"], ["word"]), str(tmp_path))

    SaveTierLayout()(TierLayout(), str(tmp_path))

    assert read(tmp_path / "phonlab.toml") == {"display": {}}
    assert LoadTierLayout()(str(tmp_path)) == TierLayout()


def test_load_reads_saved_layout(tmp_path: Path):
    SaveTierLayout()(TierLayout(["phone"], ["word", "tone"]), str(tmp_path))

    assert LoadTierLayout()(str(tmp_path)) == TierLayout(["phone"], ["word", "tone"])


def test_load_reads_the_hidden_tiers_when_there_is_no_order(tmp_path: Path):
    (tmp_path / "phonlab.toml").write_text("[display]\nhidden_tiers = ['phone']\n")

    assert LoadTierLayout()(str(tmp_path)) == TierLayout(["phone"], [])


@pytest.mark.parametrize(
    "contents",
    [
        "not [valid toml",
        "display = 3",
        "[display]\nhidden_tiers = 'phone'\ntier_order = 'word'",
        "[display]\nhidden_tiers = [1]\ntier_order = [2]",
    ],
)
def test_load_ignores_malformed_files(tmp_path: Path, contents: str):
    (tmp_path / "phonlab.toml").write_text(contents)

    assert LoadTierLayout()(str(tmp_path)) == TierLayout()


def test_load_ignores_only_the_malformed_key(tmp_path: Path):
    (tmp_path / "phonlab.toml").write_text(
        "[display]\nhidden_tiers = [1]\ntier_order = ['word']\n"
    )

    assert LoadTierLayout()(str(tmp_path)) == TierLayout([], ["word"])


def test_save_and_load_round_trip_tier_fonts(tmp_path: Path):
    layout = TierLayout([], ["word"], {"word": "Charis SIL", "phone": "Doulos SIL"})

    SaveTierLayout()(layout, str(tmp_path))

    assert read(tmp_path / "phonlab.toml")["display"]["tier_fonts"] == {
        "word": "Charis SIL",
        "phone": "Doulos SIL",
    }
    assert LoadTierLayout()(str(tmp_path)) == layout


def test_save_removes_earlier_tier_fonts_when_there_are_none(tmp_path: Path):
    SaveTierLayout()(TierLayout(tier_fonts={"word": "Charis SIL"}), str(tmp_path))

    SaveTierLayout()(TierLayout(), str(tmp_path))

    assert read(tmp_path / "phonlab.toml") == {"display": {}}


def test_load_ignores_malformed_tier_fonts(tmp_path: Path):
    (tmp_path / "phonlab.toml").write_text(
        "[display]\ntier_fonts = 'Arial'\ntier_order = ['word']\n"
    )
    assert LoadTierLayout()(str(tmp_path)) == TierLayout([], ["word"])

    (tmp_path / "phonlab.toml").write_text(
        "[display.tier_fonts]\nword = 'Charis SIL'\nphone = 3\ntone = ''\n"
    )
    assert LoadTierLayout()(str(tmp_path)) == TierLayout(
        tier_fonts={"word": "Charis SIL"}
    )
