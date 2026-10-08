"""Domain errors. Messages are written for the user and never contain internals."""


class StudyError(Exception):
    """Base class for all domain errors."""


class NotFoundError(StudyError):
    """The requested record does not exist."""


class InvalidInputError(StudyError):
    """The input is syntactically valid but makes no sense."""
