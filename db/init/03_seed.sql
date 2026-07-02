-- Users. admin has no password_hash - its password is Fernet-encrypted
-- inside app/app/services/auth.py and only decryptable with the key
-- mounted at /etc/secrets/encryption-key (challenge 2).
INSERT INTO users (username, password_hash, auth_type, role, full_name, email) VALUES
    ('admin', NULL, 'builtin', 'admin', 'Derek (former)', 'derek@wiznt.io'),
    ('testuser', 'aab5ba11ed4caf2fed3cf23c76a0e8a65a7d042fd05a16713fa1eae8e99926ca', 'standard', 'user', 'Test User', 'testuser@wiznt.io'),
    ('guest', 'ec52dd281b8c1132f2a66c0bd6d171ac14146627bf61f58d8aba55663962709d', 'standard', 'guest', 'Guest', 'guest@wiznt.io');

-- system_config.debug_flag is challenge 1 - just needs `psql` access and
-- SELECT * FROM system_config to find.
INSERT INTO system_config (key, value, description) VALUES
    ('app_name', 'OnBored', 'Application display name'),
    ('max_login_attempts', '5', 'Maximum failed login attempts'),
    ('session_timeout', '3600', 'Session timeout in seconds'),
    ('log_level', 'INFO', 'Application log level'),
    ('debug_flag', 'FLAG{1_cl0ud_expl0rer_f0und_th3_db}', 'Debug identifier - remove in production');

-- Template modules (user_id IS NULL) copied onto every new hire's account
-- by POST /api/admin/create-account with completed=false. A brand-new
-- account can never generate a report until all five are marked complete
-- (challenge 6's IncompleteModulesError).
INSERT INTO onboarding_modules (user_id, name, description, completed) VALUES
    (NULL, 'Security Basics', 'Authentication and access control fundamentals', true),
    (NULL, 'API Guidelines', 'Internal API usage and best practices', true),
    (NULL, 'Incident Response', 'Event handling and escalation procedures', true),
    (NULL, 'Company Policies', 'HR policies and code of conduct', true),
    (NULL, 'Infrastructure', 'Cloud infrastructure and deployment overview', true);

-- report_data: 31 rows whose encoded_char, XORed against the CORRECT key
-- pair [0x42, 0x1F] (alternating by sequence parity), spell out
-- FLAG{6_d4t4_f1x3d_r3p0rt_w0rks}. The app's XOR_KEYS constant ships
-- with the wrong second byte (0x0A) - see app/app/services/reports.py.
-- Row 13 (the 'f' in "f1x3d") intentionally has value = NULL to
-- reproduce the `total += value` TypeError crash (challenge 6, part 2).
INSERT INTO report_data (sequence, category, value, encoded_char, source) VALUES
    (1,  'auth',   50, 4,   'system'),
    (2,  'api',    60, 83,  'system'),
    (3,  'event',  70, 3,   'system'),
    (4,  'page',   80, 88,  'system'),
    (5,  'system', 50, 57,  'system'),
    (6,  'auth',   60, 41,  'system'),
    (7,  'api',    70, 29,  'system'),
    (8,  'event',  80, 123, 'system'),
    (9,  'page',   50, 118, 'system'),
    (10, 'system', 60, 107, 'system'),
    (11, 'auth',   70, 118, 'system'),
    (12, 'api',    80, 64,  'system'),
    (13, 'event',  NULL, 36, 'system'),
    (14, 'page',   60, 46,  'system'),
    (15, 'system', 70, 58,  'system'),
    (16, 'auth',   80, 44,  'system'),
    (17, 'api',    50, 38,  'system'),
    (18, 'event',  60, 64,  'system'),
    (19, 'page',   70, 48,  'system'),
    (20, 'system', 80, 44,  'system'),
    (21, 'auth',   50, 50,  'system'),
    (22, 'api',    60, 47,  'system'),
    (23, 'event',  70, 48,  'system'),
    (24, 'page',   80, 107, 'system'),
    (25, 'system', 50, 29,  'system'),
    (26, 'auth',   60, 104, 'system'),
    (27, 'api',    70, 114, 'system'),
    (28, 'event',  80, 109, 'system'),
    (29, 'page',   50, 41,  'system'),
    (30, 'system', 60, 108, 'system'),
    (31, 'auth',   70, 63,  'system');
