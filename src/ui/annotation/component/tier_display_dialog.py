from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.annotation.state.tier_display_state import HIDDEN_POSITION, TierDisplayState


class TierDisplayDialog(QDialog):
    """Lets the user number the annotation tiers to choose which are shown and in what
    order: 1 is the bottom of the plot, 2 the next tier up, and so on. A tier with no
    number is hidden"""

    def __init__(self, tiers: list[TierDisplayState], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Show and Order Tiers"))
        self.setMinimumWidth(340)

        self.table = QTableWidget(len(tiers), 2)
        self.table.setHorizontalHeaderLabels([self.tr("Tier"), self.tr("Position")])
        row_header = self.table.verticalHeader()
        if row_header is not None:
            row_header.setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        self.spin_boxes: list[QSpinBox] = []
        for row, tier in enumerate(tiers):
            name_item = QTableWidgetItem(tier.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 0, name_item)

            spin_box = QSpinBox()
            spin_box.setRange(HIDDEN_POSITION, len(tiers))
            spin_box.setSpecialValueText(self.tr("Hidden"))
            spin_box.setValue(tier.position)
            self.table.setCellWidget(row, 1, spin_box)
            self.spin_boxes.append(spin_box)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                self.tr(
                    "Number the tiers from the bottom of the plot up. "
                    "Tiers shown as Hidden are left out."
                )
            )
        )
        layout.addWidget(self.table)
        layout.addWidget(buttons)

    def tiers(self) -> list[TierDisplayState]:
        tiers = []
        for row, spin_box in enumerate(self.spin_boxes):
            item = self.table.item(row, 0)
            if item is not None:
                tiers.append(TierDisplayState(item.text(), spin_box.value()))
        return tiers

    @staticmethod
    def get_tiers(
        tiers: list[TierDisplayState], parent: QWidget | None = None
    ) -> list[TierDisplayState] | None:
        """The tiers with the positions the user chose, or None if cancelled"""
        dlg = TierDisplayDialog(tiers, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.tiers()
        return None
