"""Domain errors with safe messages suitable for callers and future CLI flows."""


class StoreError(RuntimeError):
    """Persistence operation failed."""


class RecordNotFound(StoreError):
    """Record is missing or belongs to another project (not disclosed)."""


class DuplicateOperation(StoreError):
    """Logical action or immutable identity already exists."""


class InvalidStateTransition(StoreError):
    """Requested change is not allowed in the current state."""


class SupersededPolicy(InvalidStateTransition):
    """A review cannot begin with an inactive policy."""
