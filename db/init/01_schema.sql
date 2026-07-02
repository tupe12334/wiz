-- Role used by the app (and by anyone who lands a shell and reads its
-- env vars / connection string off the pod). Deliberately weak password
-- to recreate "challenge 1": explore the cluster, find the DB creds.
CREATE ROLE appuser WITH LOGIN PASSWORD 'dbpassword123';

-- "The function has a 2-second timeout enforced at the database level"
-- (challenge 7): this has to be a role-level default, not a plain `SET`
-- issued mid-query. Postgres arms the statement_timeout cancellation
-- timer once, when the top-level statement starts, using whatever value
-- was in effect at that moment - a `SET`/`set_config(..., true)` run
-- from inside a function *after* that timer is already armed has no
-- effect on the currently-running statement. A role-level default is
-- applied at session start, before any statement runs, so it actually
-- works.
ALTER ROLE appuser SET statement_timeout = '2000';

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    auth_type TEXT NOT NULL DEFAULT 'standard', -- 'builtin' | 'standard'
    role TEXT NOT NULL DEFAULT 'user',           -- 'admin' | 'user' | 'guest'
    full_name TEXT,
    email TEXT,
    department TEXT,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Deliberately owned by appuser (not postgres) so the app's own DB role
-- can add an index to it - that's "challenge 7": the index is the fix.
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    resource_type TEXT NOT NULL,
    action TEXT NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE report_data (
    sequence INTEGER PRIMARY KEY,
    category TEXT NOT NULL,
    value INTEGER,             -- nullable on purpose, see challenge 6
    encoded_char INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'system', -- 'system' | 'user'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT
);

CREATE TABLE onboarding_modules (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id), -- NULL rows are the template used for new hires
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT false
);

ALTER TABLE audit_logs OWNER TO appuser;

GRANT SELECT, INSERT, UPDATE, DELETE ON users, sessions, report_data, system_config, onboarding_modules TO appuser;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO appuser;

-- Postgres 15+ revokes CREATE on the public schema from PUBLIC by
-- default. appuser owns audit_logs but still needs this to add the
-- fixing index in challenge 7 - CREATE INDEX creates a new relation in
-- the schema, which needs schema-level CREATE, not just table ownership.
GRANT CREATE ON SCHEMA public TO appuser;
