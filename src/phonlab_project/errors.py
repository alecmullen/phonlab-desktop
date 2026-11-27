class ProjectError(Exception):
    """Raised when a project does not have what was asked for, or a folder or file is not a
    project. The message says what the project does have."""
