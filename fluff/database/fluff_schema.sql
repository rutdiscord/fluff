CREATE TABLE IF NOT EXISTS sticky_message (
    id INTEGER PRIMARY KEY,
    server_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    message TEXT NOT NULL,
    last_message_id TEXT,
    last_message_timestamp INT,
    CONSTRAINT unique_sticky_message_server_channel_constraint UNIQUE (server_id, channel_id)
) strict;