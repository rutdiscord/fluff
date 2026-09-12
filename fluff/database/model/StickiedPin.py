from dataclasses import dataclass

@dataclass
class StickiedPin:
    channel_id: int # the channel ID where this pin resides in
    message_id: int # the actual pin message ID
    date_added: int # the epoch timestamp representing when this pin was added to the table