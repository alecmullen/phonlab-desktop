from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFontComboBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from res.constants import LABEL_FONT_FAMILY


def remove_bitmap_fonts(combo_box: QFontComboBox):
    """Qt lists macOS's bitmap fonts (such as "GB18030 Bitmap") as scalable, but
    fails to draw them: the drop-down, which draws each family in its own font,
    logs "Failed to compute left/right minimum bearings" for each one it shows.
    Call it after `setCurrentFont`, which fills the list again"""
    for row in reversed(range(combo_box.count())):
        if "bitmap" in combo_box.itemText(row).lower():
            combo_box.removeItem(row)


class TierFontDialog(QDialog):
    """Lets the user choose the font of the labels of each annotation tier. The tiers
    are listed as they appear in the plot, top to bottom.

    `fonts` are the font families chosen so far, by tier name. A tier it does not
    name is in the default font"""

    def __init__(
        self,
        names: list[str],
        fonts: dict[str, str],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Choose Fonts"))
        self.setMinimumWidth(400)

        self.names = names
        self.fonts = fonts

        self.table = QTableWidget(len(names), 2)
        self.table.setHorizontalHeaderLabels([self.tr("Tier"), self.tr("Font")])
        row_header = self.table.verticalHeader()
        if row_header is not None:
            row_header.setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # What each box shows at the start. A font that is not installed here, as one
        # chosen on another computer, shows as a different one, and is kept unless
        # the user changes the box
        self.combo_boxes: list[QFontComboBox] = []
        self.initial_families: list[str] = []
        for row, name in enumerate(names):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 0, name_item)

            combo_box = QFontComboBox()
            combo_box.setCurrentFont(QFont(fonts.get(name, LABEL_FONT_FAMILY)))
            remove_bitmap_fonts(combo_box)  # after setCurrentFont, which lists them
            self.table.setCellWidget(row, 1, combo_box)
            self.combo_boxes.append(combo_box)
            self.initial_families.append(combo_box.currentFont().family())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        intro = QLabel(self.tr("Choose the font of the labels of each tier."))
        intro.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.table)
        layout.addWidget(buttons)

    def chosen_fonts(self) -> dict[str, str]:
        """The font chosen for each tier that is not in the default font"""
        chosen = {}
        for name, combo_box, initial in zip(
            self.names, self.combo_boxes, self.initial_families
        ):
            family = combo_box.currentFont().family()
            if family == initial:
                family = self.fonts.get(name, LABEL_FONT_FAMILY)
            if family != LABEL_FONT_FAMILY:
                chosen[name] = family
        return chosen

    @staticmethod
    def get_fonts(
        names: list[str], fonts: dict[str, str], parent: QWidget | None = None
    ) -> dict[str, str] | None:
        """The font chosen for each tier that is not in the default font, or None if
        cancelled"""
        dlg = TierFontDialog(names, fonts, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.chosen_fonts()
        return None
