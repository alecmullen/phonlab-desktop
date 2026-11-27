from dataclasses import dataclass, field

from phonlab_project.metadata import MetadataTarget


@dataclass(frozen=True)
class InformationSource:
    """A CSV file whose columns were added to the project database, and how, so the
    same information can be added again to a new database"""

    # the file, relative to the project directory if it is inside it
    file: str
    target: MetadataTarget
    key_column: str
    # header of each column added -> the name the user wanted for it in the database
    columns: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AppliedInformation:
    """The result of adding the project's saved CSV files to its database again"""

    applied: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
