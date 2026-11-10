import pyqtgraph as pg
from PyQt6.QtGui import QColor

LIGHT_GREEN = "#00dd00"
DARK_GREEN = "#009900"


class TierSelectionIndicator:
    def __init__(self, parent_plot: pg.PlotItem):
        self.parent_plot = parent_plot

        self.left_bar = pg.PlotDataItem(
            [-1, -1],
            [-1, -1],
            pen=pg.mkPen(QColor(LIGHT_GREEN), width=4),
            symbol="d",
            symbolPen=pg.mkPen(QColor(DARK_GREEN), width=1.5),
            symbolBrush=pg.mkBrush(QColor(LIGHT_GREEN)),
            symbolSize=12,
        )

        self.right_bar = pg.PlotDataItem(
            [-1, -1],
            [-1, -1],
            pen=pg.mkPen(QColor(LIGHT_GREEN), width=4),
            symbol="d",
            symbolPen=pg.mkPen(QColor(DARK_GREEN), width=1.5),
            symbolBrush=pg.mkBrush(QColor(LIGHT_GREEN)),
            symbolSize=12,
        )
        self.left_bar.setZValue(10)
        self.right_bar.setZValue(10)

        parent_plot.addItem(self.left_bar)
        parent_plot.addItem(self.right_bar)

    def set_visible(self, value: bool):
        self.left_bar.setVisible(value)
        self.right_bar.setVisible(value)

    def set_boundaries(self, tier: int, start: float, end: float):
        self.set_visible(True)

        self.left_bar.setData([start, start], [tier, tier + 1])
        self.right_bar.setData([end, end], [tier, tier + 1])
