import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QResizeEvent


class DocumentGraphicsWidget(pg.GraphicsLayoutWidget):
    """The widget the plots of a document are laid out in. It announces when its own
    size changes in order to prompt any layout changes in the docuemnt view."""

    resized = pyqtSignal()

    def resizeEvent(self, ev: QResizeEvent | None):
        super().resizeEvent(ev)
        self.resized.emit()
