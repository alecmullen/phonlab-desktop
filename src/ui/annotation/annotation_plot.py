import pyqtgraph as pg

from ui.annotation.annotation_state import AnnotationState


class AnnotationPlot(pg.PlotItem):
    def __init__(
        self, linked_plot: pg.PlotItem | None = None, is_bottom_plot: bool = False
    ):
        super().__init__(self)
        self.getViewBox().setXLink(linked_plot)

        if is_bottom_plot:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)
        else:
            self.getAxis("bottom").setStyle(showValues=False)

    def show_time_axis(self, show: bool):
        if show:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)

    def populate(self, annotation_state: AnnotationState):
        nodes = annotation_state.nodes
        types = annotation_state.types
        self.setYRange(0, len(types), padding=0)
        self.setYTicks([type.type for type in types])
        for i, type in enumerate(types):
            for label in type.labels:
                x_e = nodes[label.e_node]
                x_s = nodes[label.s_node]
                y = [i, i + 1]
                pg.PlotDataItem([x_e, x_e], y)
                center_x = (x_e - x_s) // 2 + x_s
                center_y = i + 0.5
                pg.TextItem(label.label, anchor=(center_x, center_y))
