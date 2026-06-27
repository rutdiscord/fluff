from enum import StrEnum, auto

class RolebanType(StrEnum):
    """Enumeration of possible roleban types"""
    TOSS = auto()
    RULEPUSH = auto()