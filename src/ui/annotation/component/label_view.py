import pyqtgraph as pg
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QFont, QFontMetrics, QPainter, QPicture, QTextOption
from PyQt6.QtWidgets import QStyleOptionGraphicsItem, QWidget

from res.constants import POINT_LABEL_WIDTH
from ui.annotation.state.annotation_label_state import AnnotationLabelState


class LabelView(pg.GraphicsObject):
    def __init__(self, labels: list[AnnotationLabelState], parent_plot: pg.PlotItem):
        super().__init__()
        self.labels = labels

        self.view_rect: QRectF = parent_plot.getViewBox().viewRect()
        self.setPos(self.view_rect.left(), self.view_rect.bottom())

        pixel_size = parent_plot.getViewBox().viewPixelSize()

        for label in labels:
            label_width = int(label.size[0] / pixel_size[0])
            label_height = int(label.size[1] / pixel_size[1])

            if label_width == 0:
                label_width = POINT_LABEL_WIDTH

            text = " ".join(label.label.splitlines())

            font = QFont("Arial", 16)
            metrics = QFontMetrics(font)
            num_lines = int(label_height / (metrics.lineSpacing() * 1.5))
            clipped_text = metrics.elidedText(
                text, Qt.TextElideMode.ElideRight, label_width * num_lines
            )

            label_item = pg.TextItem(clipped_text, anchor=(0.5, 0.5), color=(0, 0, 0))
            option = label_item.textItem.document().defaultTextOption()
            option.setWrapMode(QTextOption.WrapMode.WordWrap)
            option.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_item.textItem.document().setDefaultTextOption(option)
            label_item.setFont(font)
            label_item.setTextWidth(label_width)
            label_item.setPos(*label.pos)
            label_item.setParentItem(self)

        self.pic = QPicture()
        self._generate_picture()

    def _generate_picture(self):
        painter = QPainter(self.pic)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(pg.mkBrush(0, 0, 0, 20))
        for label in self.labels:
            width, height = label.size
            painter.drawRect(
                QRectF(
                    label.pos[0] - (width / 2),
                    label.pos[1] - (height / 2),
                    width,
                    height,
                )
            )
        painter.end()

    def paint(
        self,
        painter: QPainter | None,
        option: QStyleOptionGraphicsItem | None,
        widget: QWidget | None,
    ):
        if painter is not None:
            painter.drawPicture(0, 0, self.pic)

    def boundingRect(self) -> QRectF:
        return self.view_rect
