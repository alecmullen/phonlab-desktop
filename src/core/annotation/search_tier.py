from core.annotation.entity.tier_label import MatchMode, TierLabel, label_matches
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class SearchTier(UseCaseSync[list[TierLabel]]):
    """Finds the labels on tiers named `tier_name` that match `query`, in file, then
    time order. Searches every file in the project unless `file_stem` is given"""

    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(
        self,
        tier_name: str,
        query: str,
        mode: MatchMode,
        file_stem: str | None = None,
    ) -> list[TierLabel]:
        if query == "":
            return []

        labels = self.annotation_repository.find_labels_by_tier_name(
            tier_name, file_stem
        )
        return sorted(
            (hit for hit in labels if label_matches(hit.label.label, query, mode)),
            key=TierLabel.sort_key,
        )
