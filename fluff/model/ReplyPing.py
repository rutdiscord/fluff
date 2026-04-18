from dataclasses import dataclass

@dataclass
class ReplyPing:
    message_author_id: int #the ID of the user who sent the reply ping
    ref_message_author_id: int  #the ID of the user who was reply pinged
    reply_ping_timestamp: int #epoch timestamp representing when the reply ping message was sent