import bisect

from PyQt6.QtWidgets import QComboBox, QWidget


class SampleRateDropdown(QComboBox):
    def __init__(
        self,
        sample_rates: list[int],
        current_fs: int | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        for fs in sample_rates:
            self.addItem(f"{fs} Hz", fs)

        if current_fs is not None:
            current_idx = find_nearest_value_index(sample_rates, current_fs)
            self.setCurrentIndex(current_idx)


def find_nearest_value_index(sorted_list: list[int], target: int) -> int:
    if not sorted_list:
        return 0

    idx = bisect.bisect_left(sorted_list, target)

    if idx == 0:
        return 0

    if idx == len(sorted_list):
        return len(sorted_list) - 1

    if sorted_list[idx] - target < target - sorted_list[idx - 1]:
        return idx
    else:
        return idx - 1
