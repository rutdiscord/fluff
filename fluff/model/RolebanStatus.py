from enum import StrEnum, auto

class RolebanStatus(StrEnum):
    """Enumeration of possible roleban statuses"""
    ACTIVE = auto()
    LEFT = auto()