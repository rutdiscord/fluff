CREATE TABLE starboard_channel_blacklist (
    channel_id TEXT PRIMARY KEY --channel (and threads in that channel) that we want to prevent from being sent to the starboard queue
) STRICT;