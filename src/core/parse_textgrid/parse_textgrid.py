import bisect
import re
from collections.abc import Iterator

from core.base.use_case_sync import UseCaseSync
from core.parse_textgrid.annotation import Annotation, AnnotationLabel, AnnotationType

SAME_NODE_THRESHOLD = 0.005
INTERVAL_TIER_NAME = "IntervalTier"


class ParseTextGrid(UseCaseSync):
    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename

        self.float_regex = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)$")
        self.int_regex = re.compile(r"[-+]?\d+")
        self.quote_regex = re.compile(r'"[^"]*"')

        self.token_regex = re.compile(r'"[^"]*"|\S+')

    def invoke(self) -> Annotation:
        with open(self.filename, mode="r", encoding="utf-8") as tg:
            text = tg.read()
            words = iter(re.findall(self.token_regex, text))

            _start = self.get_next_float(words)
            _end = self.get_next_float(words)

            num_tiers = self.get_next_int(words)

            node_times: list[float] = []
            labels: dict[str, list[tuple[str, float, float]]] = {}

            for _ in range(num_tiers):
                _tier_type = self.get_next_quoted_string(words)
                if _tier_type == INTERVAL_TIER_NAME:
                    tier_name = self.get_next_quoted_string(words)
                    labels[tier_name] = []

                    _tier_start = self.get_next_float(words)
                    _tier_end = self.get_next_float(words)

                    num_intervals = self.get_next_int(words)

                    for i in range(num_intervals):
                        interval_start = self.get_next_float(words)
                        interval_end = self.get_next_float(words)
                        interval_label = self.get_next_quoted_string(words)

                        node_times = get_or_add_node(node_times, interval_start)
                        node_times = get_or_add_node(node_times, interval_end)

                        labels[tier_name].append(
                            (interval_label, interval_start, interval_end)
                        )

        nodes = {idx: node for idx, node in enumerate(node_times)}
        types = []
        for tier_name, tier_labels in labels.items():
            annotation_labels = []
            for label in tier_labels:
                label_text, start_time, end_time = label
                s_node = bisect.bisect_left(node_times, start_time)
                e_node = bisect.bisect_left(node_times, end_time)
                annotation_labels.append(AnnotationLabel(s_node, e_node, label_text))

            annotation_type = AnnotationType(type=tier_name, labels=annotation_labels)
            types.append(annotation_type)

        annotation = Annotation(nodes, types)
        return annotation

    def get_next_float(self, words: Iterator[str]) -> float:
        match = get_next_match(words, self.float_regex)
        return float(match.group()) if match is not None else None

    def get_next_int(self, words: Iterator[str]) -> int:
        match = get_next_match(words, self.int_regex)
        return int(match.group()) if match is not None else None

    def get_next_quoted_string(self, words: Iterator[str]) -> str:
        match = get_next_match(words, self.quote_regex)
        return match.group()[1:-1]


def get_next_match(words: Iterator[str], regex: re.Pattern[str]) -> re.Match[str]:
    x = None
    while x is None:
        try:
            word = next(words)
        except StopIteration as e:
            raise SyntaxError("Invalid TextGrid. Missing expected token.") from e
            return None
        x = re.fullmatch(regex, word)
    return x


def get_or_add_node(node_times: list[float], new_time: float) -> list[float]:
    idx = bisect.bisect_left(node_times, new_time)

    if (
        idx < len(node_times) and abs(node_times[idx] - new_time) < SAME_NODE_THRESHOLD
    ) or (idx - 1 >= 0 and abs(node_times[idx - 1] - new_time) < SAME_NODE_THRESHOLD):
        return node_times

    bisect.insort(node_times, new_time)
    return node_times
