from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.annotation.state.tier_display_state import (
    HIDDEN_POSITION,
    TierDisplayState,
    grouped_by_talker,
    listed_as_plotted,
)


class TierDisplayDialog(QDialog):
    """Lets the user number the annotation tiers to choose which are shown and in what
    order: 1 is the bottom of the plot, 2 the next tier up, and so on. A tier with no
    number is hidden.

    The rows are laid out like the plot: the tier at the top of the plot first, and the
    hidden tiers last. `tiers` are the tiers bottom to top, then the hidden ones"""

    def __init__(self, tiers: list[TierDisplayState], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Show and Order Tiers"))
        self.setMinimumWidth(340)

        self.listed_names = [tier.name for tier in tiers]
        self.talkers = {tier.name: tier.talker for tier in tiers}
        rows = listed_as_plotted(tiers)

        self.table = QTableWidget(len(rows), 4)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("Tier"),
                self.tr("Talker"),
                self.tr("Labels"),
                self.tr("Position"),
            ]
        )
        row_header = self.table.verticalHeader()
        if row_header is not None:
            row_header.setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header_item = self.table.horizontalHeaderItem(0)
        if header_item is not None:
            header_item.setTextAlignment(_RIGHT)

        self.spin_boxes: list[QSpinBox] = []
        for row, tier in enumerate(rows):
            name_item = QTableWidgetItem(tier.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            name_item.setTextAlignment(_RIGHT)
            self.table.setItem(row, 0, name_item)

            talker_item = QTableWidgetItem(tier.talker or "")
            talker_item.setFlags(talker_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 1, talker_item)

            count_item = QTableWidgetItem(str(tier.n_labels))
            count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            count_item.setTextAlignment(_RIGHT)
            self.table.setItem(row, 2, count_item)

            spin_box = QSpinBox()
            spin_box.setRange(HIDDEN_POSITION, len(rows))
            spin_box.setSpecialValueText(self.tr("Hidden"))
            spin_box.setValue(tier.position)
            self.table.setCellWidget(row, 3, spin_box)
            self.spin_boxes.append(spin_box)

        # Only a file whose tiers say who produced them has talkers to group by
        self.table.setColumnHidden(1, not any(self.talkers.values()))
        self.group_button = QPushButton(self.tr("Group Tiers by Talker"))
        self.group_button.setVisible(any(self.talkers.values()))
        self.group_button.clicked.connect(self.group_by_talker)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        intro = QLabel(
            self.tr(
                "Tiers are listed as they appear in the plot, top to bottom, with "
                "the number of labels each has in this file. The tier with the lowest "
                "number is shown at the bottom of the display."
            )
        )
        intro.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.table)
        layout.addWidget(self.group_button)
        layout.addWidget(buttons)

    def group_by_talker(self):
        """Number the shown tiers again so that the tiers of one talker are together"""
        grouped = grouped_by_talker(
            [
                TierDisplayState(
                    tier.name, tier.position, talker=self.talkers[tier.name]
                )
                for tier in self.tiers()
            ]
        )
        positions = {tier.name: tier.position for tier in grouped}
        for row, spin_box in enumerate(self.spin_boxes):
            item = self.table.item(row, 0)
            if item is not None:
                spin_box.setValue(positions[item.text()])

    def tiers(self) -> list[TierDisplayState]:
        """The tiers with the positions now chosen, in the order they were given"""
        positions = {}
        for row, spin_box in enumerate(self.spin_boxes):
            item = self.table.item(row, 0)
            if item is not None:
                positions[item.text()] = spin_box.value()
        return [TierDisplayState(name, positions[name]) for name in self.listed_names]

    @staticmethod
    def get_tiers(
        tiers: list[TierDisplayState], parent: QWidget | None = None
    ) -> list[TierDisplayState] | None:
        """The tiers with the positions the user chose, or None if cancelled"""
        dlg = TierDisplayDialog(tiers, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.tiers()
        return None


_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
