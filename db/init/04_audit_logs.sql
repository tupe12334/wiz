-- 150,000 synthetic rows. Combined with the forced nested-loop plan in
-- analyze_burst_activity(), the correlated EXISTS subquery here blows
-- past the 2s statement_timeout without a supporting index (challenge 7).
INSERT INTO audit_logs (user_id, resource_type, action, "timestamp")
SELECT
    (random() * 999 + 1)::int AS user_id,
    (ARRAY['document', 'page', 'api'])[floor(random() * 3 + 1)] AS resource_type,
    (ARRAY['view', 'edit', 'delete', 'download'])[floor(random() * 4 + 1)] AS action,
    now() - (random() * interval '30 days')
FROM generate_series(1, 150000);

ANALYZE audit_logs;
