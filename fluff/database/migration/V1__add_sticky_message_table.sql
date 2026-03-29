CREATE TABLE sticky_message (
    server_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    message TEXT NOT NULL,
    last_message_id TEXT,
    PRIMARY KEY (server_id, channel_id),
    CONSTRAINT unique_sticky_message_server_channel_constraint UNIQUE (server_id, channel_id)
) STRICT;