import pyqtgraph as pg
from PyQt6.QtGui import QFont
from pyqtgraph.Qt import QtCore, QtGui


class LabelView(pg.GraphicsObject):
    def __init__(self, size: tuple, label: str):
        super().__init__()
        self.size = size
        self.label = label

        label_item = pg.TextItem(self.label, anchor=(0.5, 0.5), color=(0, 0, 0))
        label_item.setFont(QFont("Arial", 16))
        label_item.setPos(0, 0)
        label_item.setParentItem(self)

        self.pic = QtGui.QPicture()
        self._generate_picture()
        
    def _generate_picture(self):
        width, height = self.size

        painter = QtGui.QPainter(self.pic)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(pg.mkBrush(0, 0, 0, 20))
        painter.drawRect(QtCore.QRectF(-width/2, -height/2, width, height))
        painter.end()

    def paint(self, p, opt, widget):
        p.drawPicture(0, 0, self.pic)

    def boundingRect(self):
        width, height = self.size
        return QtCore.QRectF(-width/2, -height/2, width, height)
