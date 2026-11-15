from dataclasses import replace

from core.annotation.entity.tier_label import MatchMode, TierLabel, replace_in_label
from core.annotation.update_label import UpdateLabel
from core.base.use_case_sync import UseCaseSync


class ReplaceInTier(UseCaseSync[list[TierLabel]]):
    """Rewrites the text of the given labels, swapping `query` for `replacement`.
    Returns the labels as updated"""

    def __init__(self, update_label: UpdateLabel):
        self.update_label = update_label

    def __call__(
        self,
        labels: list[TierLabel],
        query: str,
        replacement: str,
        mode: MatchMode,
    ) -> list[TierLabel]:
        updated = []
        for tier_label in labels:
            text = replace_in_label(tier_label.label.label, query, replacement, mode)
            new_label = replace(tier_label.label, label=text)
            self.update_label(new_label)
            updated.append(replace(tier_label, label=new_label))
        return updated
