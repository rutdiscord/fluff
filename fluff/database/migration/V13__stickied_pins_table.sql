CREATE TABLE stickied_pins (
    channel_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    date_added INTEGER NOT NULL,
    PRIMARY KEY (channel_id, message_id)
) STRICT;