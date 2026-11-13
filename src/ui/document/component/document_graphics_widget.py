import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QResizeEvent


class DocumentGraphicsWidget(pg.GraphicsLayoutWidget):
    """The widget the plots of a document are laid out in. It announces when its own
    size changes: the plot rows are sized from its height, which is not yet up to
    date when the page around it is resized (a tab opened in the background has not
    had its contents resized until it is first shown)"""

    resized = pyqtSignal()

    def resizeEvent(self, ev: QResizeEvent | None):
        super().resizeEvent(ev)
        self.resized.emit()
