CREATE TABLE whitelist_ping (
    user_id TEXT NOT NULL,
    whitelisted_user_id TEXT NOT NULL,
    PRIMARY KEY (user_id, whitelisted_user_id)
) STRICT;