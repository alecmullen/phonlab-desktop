import pyqtgraph as pg


class AnnotationPlot(pg.PlotItem):

    def __init__(self):
        pass

    def show_time_axis(self, show: bool):
        if show:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)
        else:
            self.wave_plot.getAxis("bottom").setStyle(showValues=False)

    def populate(self):
        pass