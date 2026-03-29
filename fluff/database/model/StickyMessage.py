from dataclasses import dataclass


@dataclass
class StickyEntry:
    message: str #the content of the sticky message
    last_sticky_message_id: int | None #the id of the last sticky discord message