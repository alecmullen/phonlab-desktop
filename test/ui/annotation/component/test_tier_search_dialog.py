from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot
from support.mocks import mock_view_model

from ui.annotation.component.tier_search_dialog import TierSearchDialog
from ui.annotation.state.tier_search_state import TierSearchState
from ui.annotation.tier_search_view_model import TierSearchViewModel


@pytest.fixture
def view_model() -> MagicMock:
    return mock_view_model(TierSearchViewModel)


@pytest.fixture
def dialog(qtbot: QtBot, view_model: MagicMock) -> TierSearchDialog:
    dlg = TierSearchDialog(view_model)
    qtbot.addWidget(dlg)
    # The mock records `subscribe` rather than connecting, so connect by hand
    view_model.subscribe.assert_called_once_with(dlg.on_state_change)
    view_model.state_changed.connect(dlg.on_state_change)
    return dlg


def test_is_not_modal(dialog: TierSearchDialog):
    assert dialog.windowModality() == Qt.WindowModality.NonModal


def test_buttons_disabled_until_query_typed(qtbot: QtBot, dialog: TierSearchDialog):
    assert not dialog.find_button.isEnabled()
    assert not dialog.replace_button.isEnabled()
    assert not dialog.replace_all_button.isEnabled()

    qtbot.keyClicks(dialog.find_edit, "cat")

    assert dialog.find_button.isEnabled()
    assert dialog.replace_button.isEnabled()
    assert dialog.replace_all_button.isEnabled()


def test_state_shows_tier_and_message(dialog: TierSearchDialog, view_model: MagicMock):
    view_model.state_changed.emit(TierSearchState("words", True, "No matches"))

    assert dialog.tier_label.text() == "words"
    assert dialog.message_label.text() == "No matches"
    assert dialog.project_checkbox.isEnabled()


def test_project_option_disabled_and_cleared_without_project(
    dialog: TierSearchDialog, view_model: MagicMock
):
    view_model.state_changed.emit(TierSearchState("words", True))
    dialog.project_checkbox.setChecked(True)

    view_model.state_changed.emit(TierSearchState("words", False))

    assert not dialog.project_checkbox.isEnabled()
    assert not dialog.project_checkbox.isChecked()


def test_find_next_passes_query_and_options(
    qtbot: QtBot, dialog: TierSearchDialog, view_model: MagicMock
):
    view_model.state_changed.emit(TierSearchState("words", True))
    qtbot.keyClicks(dialog.find_edit, "cat")
    dialog.project_checkbox.setChecked(True)

    qtbot.mouseClick(dialog.find_button, Qt.MouseButton.LeftButton)

    view_model.find_next.assert_called_once_with("cat", False, True)


def test_return_in_find_field_finds_next(
    qtbot: QtBot, dialog: TierSearchDialog, view_model: MagicMock
):
    qtbot.keyClicks(dialog.find_edit, "cat")

    qtbot.keyClick(dialog.find_edit, Qt.Key.Key_Return)

    view_model.find_next.assert_called_once_with("cat", False, False)


def test_whole_label_option_requests_exact_match(
    qtbot: QtBot, dialog: TierSearchDialog, view_model: MagicMock
):
    qtbot.keyClicks(dialog.find_edit, "cat")
    dialog.match_selector.setCurrentIndex(1)

    dialog.find_next()

    view_model.find_next.assert_called_once_with("cat", True, False)


def test_replace_passes_replacement(
    qtbot: QtBot, dialog: TierSearchDialog, view_model: MagicMock
):
    qtbot.keyClicks(dialog.find_edit, "cat")
    qtbot.keyClicks(dialog.replace_edit, "dog")

    qtbot.mouseClick(dialog.replace_button, Qt.MouseButton.LeftButton)

    view_model.replace.assert_called_once_with("cat", "dog", False, False)


def test_replace_all_passes_replacement(
    qtbot: QtBot, dialog: TierSearchDialog, view_model: MagicMock
):
    qtbot.keyClicks(dialog.find_edit, "cat")
    qtbot.keyClicks(dialog.replace_edit, "dog")

    qtbot.mouseClick(dialog.replace_all_button, Qt.MouseButton.LeftButton)

    view_model.replace_all.assert_called_once_with("cat", "dog", False, False)


def test_empty_query_does_nothing(dialog: TierSearchDialog, view_model: MagicMock):
    dialog.find_next()
    dialog.replace()
    dialog.replace_all()

    view_model.find_next.assert_not_called()
    view_model.replace.assert_not_called()
    view_model.replace_all.assert_not_called()


def test_show_and_focus_shows_dialog(qtbot: QtBot, dialog: TierSearchDialog):
    dialog.show_and_focus()

    assert dialog.isVisible()
