import pyqtgraph as pg
from pytestqt.qtbot import QtBot

from ui.annotation.component.tier_selection_indicator import TierSelectionIndicator


def _bars(indicator: TierSelectionIndicator) -> list[pg.PlotDataItem]:
    return [indicator.left_bar, indicator.right_bar]


def test_indicator_adds_bars_to_parent_plot(qtbot: QtBot):
    plot = pg.PlotItem()

    indicator = TierSelectionIndicator(plot)

    assert indicator.left_bar in plot.items
    assert indicator.right_bar in plot.items


def test_indicator_bars_draw_above_plot_items(qtbot: QtBot):
    indicator = TierSelectionIndicator(pg.PlotItem())

    assert [bar.zValue() for bar in _bars(indicator)] == [10, 10]


def test_set_boundaries_places_bars_across_tier(qtbot: QtBot):
    indicator = TierSelectionIndicator(pg.PlotItem())

    indicator.set_boundaries(2, 0.5, 1.5)

    left_x, left_y = indicator.left_bar.getData()
    right_x, right_y = indicator.right_bar.getData()
    assert list(left_x) == [0.5, 0.5]
    assert list(right_x) == [1.5, 1.5]
    assert list(left_y) == [2, 3]
    assert list(right_y) == [2, 3]


def test_set_boundaries_makes_bars_visible(qtbot: QtBot):
    indicator = TierSelectionIndicator(pg.PlotItem())
    indicator.set_visible(False)

    indicator.set_boundaries(0, 0.0, 1.0)

    assert all(bar.isVisible() for bar in _bars(indicator))


def test_set_visible_false_hides_both_bars(qtbot: QtBot):
    indicator = TierSelectionIndicator(pg.PlotItem())
    indicator.set_boundaries(0, 0.0, 1.0)

    indicator.set_visible(False)

    assert not any(bar.isVisible() for bar in _bars(indicator))
