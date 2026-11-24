import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from ui.annotation.component.tier_display_dialog import TierDisplayDialog
from ui.annotation.state.tier_display_state import TierDisplayState

# As the view model lists them: bottom of the plot to the top, then the hidden ones
TIERS = [
    TierDisplayState("phone", 1),
    TierDisplayState("word", 2),
    TierDisplayState("tone"),
]


def make_dialog(qtbot: QtBot) -> TierDisplayDialog:
    dialog = TierDisplayDialog(TIERS)
    qtbot.addWidget(dialog)
    return dialog


def row_names(dialog: TierDisplayDialog) -> list[str]:
    return [dialog.table.item(row, 0).text() for row in range(dialog.table.rowCount())]


def test_rows_run_from_the_top_of_the_plot_down_then_the_hidden_tiers(qtbot: QtBot):
    assert row_names(make_dialog(qtbot)) == ["word", "phone", "tone"]


def test_each_row_shows_the_position_of_its_tier(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    assert [box.value() for box in dialog.spin_boxes] == [2, 1, 0]


def test_tier_names_are_right_aligned(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    for row in range(dialog.table.rowCount()):
        alignment = dialog.table.item(row, 0).textAlignment()
        assert alignment & Qt.AlignmentFlag.AlignRight


def test_a_tier_without_a_position_reads_hidden(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    assert dialog.spin_boxes[2].text() == "Hidden"


def test_positions_go_up_to_the_number_of_tiers(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    assert all(box.minimum() == 0 and box.maximum() == 3 for box in dialog.spin_boxes)


def test_tiers_are_returned_in_the_order_they_were_given(qtbot: QtBot):
    assert make_dialog(qtbot).tiers() == TIERS


def test_tiers_reflect_the_positions_that_were_typed(qtbot: QtBot):
    dialog = make_dialog(qtbot)

    dialog.spin_boxes[0].setValue(0)  # word
    dialog.spin_boxes[2].setValue(3)  # tone

    assert dialog.tiers() == [
        TierDisplayState("phone", 1),
        TierDisplayState("word"),
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


def test_each_row_shows_how_many_labels_its_tier_has(qtbot: QtBot):
    dialog = TierDisplayDialog(
        [TierDisplayState("phone", 1, 43), TierDisplayState("word", 2, 10)]
    )
    qtbot.addWidget(dialog)

    assert [dialog.table.item(row, 2).text() for row in range(2)] == ["10", "43"]
    assert dialog.table.horizontalHeaderItem(2).text() == "Labels"
    assert [box.value() for box in dialog.spin_boxes] == [2, 1]


TALKER_TIERS = [
    TierDisplayState("a-words", 1, talker="ann"),
    TierDisplayState("b-words", 2, talker="bob"),
    TierDisplayState("a-phones", 3, talker="ann"),
    TierDisplayState("b-phones", 4, talker="bob"),
    TierDisplayState("notes", 5),
]


def test_the_talker_column_and_button_are_there_only_when_tiers_have_talkers(
    qtbot: QtBot,
):
    plain = make_dialog(qtbot)
    plain.show()
    assert plain.table.isColumnHidden(1)
    assert not plain.group_button.isVisible()

    dialog = TierDisplayDialog(TALKER_TIERS)
    qtbot.addWidget(dialog)
    dialog.show()

    assert not dialog.table.isColumnHidden(1)
    assert dialog.group_button.isVisible()
    assert [dialog.table.item(row, 1).text() for row in range(5)] == [
        "",
        "bob",
        "ann",
        "bob",
        "ann",
    ]


def test_grouping_by_talker_numbers_the_tiers_of_each_talker_together(qtbot: QtBot):
    dialog = TierDisplayDialog(TALKER_TIERS)
    qtbot.addWidget(dialog)

    dialog.group_button.click()

    chosen = {tier.name: tier.position for tier in dialog.tiers()}
    assert chosen == {
        "a-words": 1,
        "a-phones": 2,
        "b-words": 3,
        "b-phones": 4,
        "notes": 5,
    }
