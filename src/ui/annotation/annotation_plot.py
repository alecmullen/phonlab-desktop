import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget

from ui.annotation.annotation_state import AnnotationState
from ui.annotation.annotation_view_model import AnnotationViewModel


class AnnotationPlot(pg.PlotItem):
    def __init__(
        self,
        parent: QWidget | None = None,
        view_model: AnnotationViewModel = None,
        linked_plot: pg.PlotItem | None = None,
        is_bottom_plot: bool = False
    ):
        super().__init__(parent)

        self.view_model = view_model

        self.getViewBox().setXLink(linked_plot)

        if is_bottom_plot:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)
        else:
            self.getAxis("bottom").setStyle(showValues=False)

        self.populate(self.view_model.annotation_state)

    def show_time_axis(self, show: bool):
        if show:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)

    def populate(self, annotation_state: AnnotationState):
        nodes = annotation_state.nodes
        types = annotation_state.types
        self.setYRange(0, len(types), padding=0)
        self.getAxis("left").setTicks([[(i, type.type) for i, type in enumerate(types)]])
        for i, type in enumerate(types):
            for label in type.labels:
                x_e = nodes[label.e_node]
                x_s = nodes[label.s_node]
                y = [i, i + 1]
                boundary = pg.PlotDataItem([x_e, x_e], y)
                self.addItem(boundary)
                center_x = (x_e - x_s) / 2 + x_s
                center_y = i + 0.5
                label_item = pg.TextItem(label.label, anchor=(0.5, 0.5))
                label_item.setPos(center_x, center_y)
                self.addItem(label_item)
