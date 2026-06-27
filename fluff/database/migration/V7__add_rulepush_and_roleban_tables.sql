CREATE TABLE rule (
    id INTEGER PRIMARY KEY,
    server_id TEXT NOT NULL,
    rule_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    CONSTRAINT unique_rule_number_server_constraint UNIQUE (server_id, rule_number)
) STRICT;

CREATE TABLE rule_push_keyword (
    server_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    PRIMARY KEY (server_id, keyword)
) STRICT;

CREATE TABLE roleban_session (
    id INTEGER PRIMARY KEY,
    server_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    type TEXT NOT NULL,
    created_at TEXT NOT NULL
) STRICT;

CREATE TABLE roleban_session_user (
    session_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL,
    rolebanned_by TEXT NOT NULL,
    PRIMARY KEY (session_id, user_id),
    FOREIGN KEY (session_id) REFERENCES roleban_session (id) ON DELETE CASCADE,
    CONSTRAINT unique_roleban_session_user_constraint UNIQUE (user_id)
) STRICT;

-- The roles the users had before being rolebanned, restored on release.
CREATE TABLE roleban_session_user_role (
    session_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (session_id) REFERENCES roleban_session (id) ON DELETE CASCADE
) STRICT;

-- The keywords hidden in the rules for this session, and whether each has
-- been found yet.
CREATE TABLE rule_push_session_keyword (
    session_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    found INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (session_id, keyword),
    FOREIGN KEY (session_id) REFERENCES roleban_session (id) ON DELETE CASCADE
) STRICT;