import itertools
import logging
import re
from enum import StrEnum

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from core.base.use_case import UseCase

SHORT_PREAMBLE = """File type = "ooTextFile"
Object class = "TextGrid"

{}
{}
<exists>
{}"""

LONG_PREAMBLE = """File type = "ooTextFile"
Object class = "TextGrid"

xmin = {}
xmax = {}
tiers? <exists>
size = {}
item []:"""


class TextgridType(StrEnum):
    SHORT = "short"
    LONG = "long"


logger = logging.getLogger(__name__)


class WriteTextGrid(UseCase):
    def _praat_short_preamble(self, xmin: str, xmax: str, tiercnt: int) -> str:
        """
        Preamble of a short Praat textgrid.
        """
        # xmin and xmax should already be strings
        return SHORT_PREAMBLE.format(xmin, xmax, str(tiercnt))

    def _praat_long_preamble(self, xmin: str, xmax: str, tiercnt: int) -> str:
        """
        Preamble of a long Praat textgrid.
        """
        # xmin and xmax should already be strings
        return LONG_PREAMBLE.format(xmin, xmax, str(tiercnt))

    def _to_praat_short_tier(
        self,
        type: AnnotationType,
        nodes: dict[int, float],
        is_point_tier: bool,
        xmin: str,
        xmax: str,
    ) -> str:
        """
        Return a string representing the a tier defined in a dataframe in
        praat_short format.
        """

        lines = [
            '"IntervalTier"' if not is_point_tier else '"TextTier"',
            '"' + type.type + '"',
            xmin,
            xmax,
            str(len(type.labels)),
        ]
        if len(type.labels) > 0:
            lines.append(self._to_praat_short_label_str(type.labels, nodes, is_point_tier))
        return "\n".join(lines)

    def _to_praat_long_tier(
        self,
        idx: int,
        type: AnnotationType,
        nodes: dict[int, float],
        is_point_tier: bool,
        xmin: str,
        xmax: str,
    ) -> str:
        """
        Return a string representing a tier defined in a dataframe in
        praat_long format.
        """

        tclass = '"IntervalTier"' if not is_point_tier else '"TextTier"'
        sizelbl = "intervals" if not is_point_tier else "points"
        tier = f"""    item [{idx}]:
        class = {tclass}
        name = "{type.type}"
        xmin = {xmin}
        xmax = {xmax}
        {sizelbl}: size = {len(type.labels)!s}"""
        if len(type.labels) > 0:
            tier += "\n        " + self._to_praat_long_label_str(
                type.labels, nodes, is_point_tier
            )
        return tier

    def _to_praat_short_label_str(
        self, labels: list[AnnotationLabel], nodes: dict[int, float], is_point_tier: bool
    ) -> str:
        """
        Return a string representing the labels of a tier in praat_short format.
        """

        ts = [
            f"{nodes[label.s_node]}\n{nodes[label.e_node]}"
            if not is_point_tier
            else f"{nodes[label.s_node]}"
            for label in labels
        ]
        replacements = [('"', '""'), (r'^', '"'), (r"\Z", '"')]
        texts = []
        for label in labels:
            text = label.label
            for pattern, repl in replacements:
                text = re.sub(pattern, repl, text)
            texts.append(text)

        return "\n".join([f"{t}\n{txt}" for t, txt in zip(ts, texts)])

    def _to_praat_long_label_str(
        self,
        labels: list[AnnotationLabel],
        nodes: dict[int, float],
        is_point_tier: bool,
    ) -> str:
        """
        Return a string representing the labels of a tier in praat_long format
        from a dataframe.
        """

        intvl = "{} [{{}}]:\n            ".format(
            "intervals" if not is_point_tier else "points"
        )

        ts = [
            f"{intvl.format(idx + 1)}xmin = {nodes[label.s_node]}\n            xmax = {nodes[label.e_node]}"
            if not is_point_tier
            else f"{intvl.format(idx + 1)}number = {nodes[label.s_node]}"
            for idx, label in enumerate(labels)
        ]
        replacements = [('"', '""'), (r"\Z", '"')]
        texts = []
        for label in labels:
            text = label.label
            for pattern, repl in replacements:
                text = re.sub(pattern, repl, text)
            texts.append(text)

        label_name = "mark" if is_point_tier else "text"
        return "\n        ".join(
            [f'{t}\n            {label_name} = "{txt}' for t, txt in zip(ts, texts)]
        )

    def __call__(
        self,
        annotation: Annotation,
        file_path: str,
        tg_type: TextgridType = TextgridType.SHORT,
        codec: str = "utf-8",
        allow_overlaps: bool = False,
    ):
        # Find max/min times.
        xmin = min(time for time in annotation.nodes.values())
        xmax = max(time for time in annotation.nodes.values())

        # Create TextGrid preamble.
        if tg_type != TextgridType.LONG:
            tg = self._praat_short_preamble(str(xmin), str(xmax), len(annotation.types))
        else:
            tg = self._praat_long_preamble(str(xmin), str(xmax), len(annotation.types))

        for tier_idx, type in enumerate(annotation.types):
            labels = sorted(
                type.labels, key=lambda label: annotation.nodes[label.s_node]
            )
            is_point_tier = all(label.e_node == label.s_node for label in labels)
            try:
                if not is_point_tier:
                    assert all(
                        annotation.nodes[label.e_node] >= annotation.nodes[label.s_node]
                        for label in labels
                    )
            except AssertionError:
                raise RuntimeError(
                    f'Found bad interval times in tier "{type.type}". End values must be greater than the start values for all labels.'
                ) from None
            try:
                # Every t1 must be >= the preceding t2.
                if not is_point_tier:
                    assert all(
                        annotation.nodes[label_2.s_node]
                        >= annotation.nodes[label_1.e_node]
                        for label_1, label_2 in itertools.pairwise(labels)
                    )
            except AssertionError:
                if allow_overlaps is True:
                    logger.error(
                        f'Found interval labels that overlap in time in tier "{type.type}". The textgrid will not be readable in Praat.\n'
                    )
                else:
                    raise RuntimeError(
                        f'Dataframe interval labels cannot overlap in time, and an overlap was found in tier "{type.type}". Use `allow_overlaps=True` to ignore this error and produce a textgrid that is not readable in Praat.'
                    ) from None

            if tg_type != TextgridType.LONG:
                tiertext = self._to_praat_short_tier(
                    type, annotation.nodes, is_point_tier, str(xmin), str(xmax)
                )
            else:
                tiertext = self._to_praat_long_tier(
                    tier_idx,
                    type,
                    annotation.nodes,
                    is_point_tier,
                    str(xmin),
                    str(xmax),
                )
            tg += f"\n{tiertext}"

        with open(file_path, "w", encoding=codec) as out:
            out.write(tg)
            yield
