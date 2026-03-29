CREATE TABLE migration_schema_history (
    version INTEGER NOT NULL,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_schema_version_constraint UNIQUE(version)
) STRICT;