from core.base.use_case_sync import UseCaseSync
from phonlab_project.readers.metadata_table import MetadataTable
from phonlab_project.readers.read_metadata_csv import read_metadata_csv


class ReadMetadataCsv(UseCaseSync[MetadataTable]):
    """Reads a CSV file whose first row names the columns (see `read_metadata_csv`).
    Raises ValueError if the file has no rows."""

    def __call__(self, path: str) -> MetadataTable:
        return read_metadata_csv(path)
