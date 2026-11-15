import pytest
from PyQt6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from res.constants import LABEL_FONT_FAMILY
from ui.annotation.component.tier_font_dialog import TierFontDialog


def make_dialog(qtbot: QtBot, fonts: dict[str, str] | None = None) -> TierFontDialog:
    dialog = TierFontDialog(["word", "phone"], fonts or {})
    qtbot.addWidget(dialog)
    return dialog


def test_rows_are_the_tiers_in_the_order_given(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    assert [dialog.table.item(row, 0).text() for row in range(2)] == ["word", "phone"]


def test_a_tier_without_a_font_starts_in_the_default_font(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    assert dialog.chosen_fonts() == {}
    assert dialog.combo_boxes[0].currentFont().family() == LABEL_FONT_FAMILY


def other_family(dialog: TierFontDialog) -> str:
    """An installed font family that is not the default"""
    combo_box = dialog.combo_boxes[0]
    return next(
        combo_box.itemText(i)
        for i in range(combo_box.count())
        if combo_box.itemText(i) != LABEL_FONT_FAMILY
    )


def test_a_tier_starts_in_its_font(qtbot: QtBot):
    family = other_family(make_dialog(qtbot))

    dialog = make_dialog(qtbot, {"phone": family})

    assert dialog.combo_boxes[1].currentFont().family() == family
    assert dialog.chosen_fonts() == {"phone": family}


def test_chosen_fonts_leave_out_tiers_in_the_default_font(qtbot: QtBot):
    dialog = make_dialog(qtbot)
    other = other_family(dialog)

    dialog.combo_boxes[0].setCurrentIndex(dialog.combo_boxes[0].findText(other))

    assert dialog.chosen_fonts() == {"word": other}

    dialog.combo_boxes[0].setCurrentIndex(
        dialog.combo_boxes[0].findText(LABEL_FONT_FAMILY)
    )

    assert dialog.chosen_fonts() == {}


def test_a_font_that_is_not_installed_is_kept_unless_changed(qtbot: QtBot):
    dialog = make_dialog(qtbot, {"word": "No Such Font Installed"})

    assert dialog.chosen_fonts() == {"word": "No Such Font Installed"}


def test_get_fonts_returns_the_choice_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)

    assert TierFontDialog.get_fonts(["word"], {"word": "No Such Font"}) == {
        "word": "No Such Font"
    }


def test_get_fonts_returns_none_when_cancelled(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Rejected)

    assert TierFontDialog.get_fonts(["word"], {}) is None


def test_bitmap_fonts_are_not_offered(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    for combo_box in dialog.combo_boxes:
        families = [combo_box.itemText(i) for i in range(combo_box.count())]
        assert not any("bitmap" in family.lower() for family in families)
