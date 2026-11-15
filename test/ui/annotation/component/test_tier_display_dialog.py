import pytest
from PyQt6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from ui.annotation.component.tier_display_dialog import TierDisplayDialog
from ui.annotation.state.tier_display_state import TierDisplayState

TIERS = [
    TierDisplayState("word", 2),
    TierDisplayState("phone", 1),
    TierDisplayState("tone"),
]


def make_dialog(qtbot: QtBot) -> TierDisplayDialog:
    dialog = TierDisplayDialog(TIERS)
    qtbot.addWidget(dialog)
    return dialog


def test_dialog_lists_tiers_with_their_positions(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    assert dialog.tiers() == TIERS
    assert [dialog.table.item(row, 0).text() for row in range(3)] == [
        "word",
        "phone",
        "tone",
    ]


def test_a_tier_without_a_position_reads_hidden(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    assert dialog.spin_boxes[2].text() == "Hidden"


def test_positions_go_up_to_the_number_of_tiers(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    assert all(box.minimum() == 0 and box.maximum() == 3 for box in dialog.spin_boxes)


def test_tiers_reflect_the_positions_that_were_typed(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    dialog.spin_boxes[0].setValue(0)
    dialog.spin_boxes[2].setValue(3)

    assert dialog.tiers() == [
        TierDisplayState("word"),
        TierDisplayState("phone", 1),
        TierDisplayState("tone", 3),
    ]


def test_get_tiers_returns_the_choice_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)

    assert TierDisplayDialog.get_tiers(TIERS) == TIERS


def test_get_tiers_returns_none_when_cancelled(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Rejected)

    assert TierDisplayDialog.get_tiers(TIERS) is None
