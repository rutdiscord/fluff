CREATE TABLE tempban (
    banned_user_id TEXT NOT NULL,
    banned_by_id TEXT NOT NULL,
    server_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    date_to_unban INTEGER NOT NULL,
    PRIMARY KEY (banned_user_id, server_id)
) STRICT;