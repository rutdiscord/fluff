CREATE TABLE ping_violation_acknowledgement (
    server_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    PRIMARY KEY (server_id, user_id)
) STRICT;