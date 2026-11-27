from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync
from core.import_words.entity.word_table import WordMatch
from phonlab_project.readers.metadata_table import MetadataTable


class MatchWords(UseCaseSync[WordMatch]):
    """Checks which of the words in a tier of the project a table has. The first column
    of the table has the words; they are compared as they are written (the case counts),
    with the label text of the labels of the tier."""

    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(self, table: MetadataTable, tier: str) -> WordMatch:
        words = [row[0] for row in table.rows if row[0] != ""]
        in_table = set(words)
        in_tier = self.annotation_repository.tier_label_counts(tier)
        return WordMatch(
            tier=tier,
            n_rows=len(words),
            n_duplicates=len(words) - len(in_table),
            n_words=len(in_tier),
            n_found=len(in_table & in_tier.keys()),
            unmatched={
                word: count for word, count in in_tier.items() if word not in in_table
            },
        )
