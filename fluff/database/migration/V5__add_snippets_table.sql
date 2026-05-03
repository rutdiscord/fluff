CREATE TABLE snippets (
    id INTEGER PRIMARY KEY,
    server_id TEXT NOT NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    CONSTRAINT unique_snippets_server_name_constraint UNIQUE (server_id, name)
) STRICT;

CREATE TABLE snippets_alias (
    id INTEGER PRIMARY KEY,
    snippet_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    CONSTRAINT fk_snippets_id_constraint FOREIGN KEY (snippet_id) REFERENCES snippets(id) ON DELETE CASCADE
) STRICT;