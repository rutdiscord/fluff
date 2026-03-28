from dataclasses import dataclass


@dataclass
class StickyEntry:
    message: str #the content of the sticky message
    db_sticky_message_id: int #the primary key representing this sticky message in the database
    last_sticky_message_id: int | None #the id of the last sticky discord message
    last_sticky_message_ts: int | None #epoch timestamp representing when the last sticky discord message was sent