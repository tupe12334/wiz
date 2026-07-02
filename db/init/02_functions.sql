-- Owned by postgres (the init script connects as POSTGRES_USER=postgres),
-- so SECURITY DEFINER gives it superuser-level pg_read_file access even
-- though the app only ever connects as the unprivileged `appuser`.
--
-- "challenge 7": the WHERE ... AND EXISTS (correlated subquery against
-- audit_logs, with no supporting index) blows past appuser's 2-second
-- statement_timeout default (see 01_schema.sql), so the flag never gets
-- read. Fix: add an index that lets the correlated subquery use an
-- index scan instead of a per-row sequential scan.
--
-- The enable_hashjoin/enable_mergejoin=off below is Derek's fingerprint
-- on this bug: modern Postgres is smart enough to rewrite a plain
-- correlated EXISTS into an efficient hash semi-join on its own, which
-- would make this fast even without an index. Derek force-disabled both
-- alternate join strategies ("nested loop is more predictable" - his
-- PR comment, may he rest) so only a real supporting index gets him out
-- of an O(n^2) scan.
CREATE OR REPLACE FUNCTION public.analyze_burst_activity()
RETURNS TABLE(status text, total_users integer, total_bursts bigint, top_users jsonb, flag text)
LANGUAGE plpgsql
SECURITY DEFINER
AS $function$
DECLARE
    flag_value TEXT;
    user_count INTEGER;
    burst_total BIGINT;
    users_json JSONB;
    start_time TIMESTAMP;
    elapsed_ms INTEGER;
BEGIN
    start_time := clock_timestamp();

    PERFORM set_config('enable_hashjoin', 'off', true);
    PERFORM set_config('enable_mergejoin', 'off', true);

    WITH burst_users AS (
        SELECT a.user_id, COUNT(*) as burst_count
        FROM audit_logs a
        WHERE a.resource_type = 'document'
          AND a.timestamp > NOW() - INTERVAL '30 days'
          AND EXISTS (
              SELECT 1 FROM audit_logs b
              WHERE b.user_id = a.user_id
                AND b.resource_type = 'document'
                AND b.timestamp > a.timestamp
          )
        GROUP BY a.user_id
    )
    SELECT
        COUNT(DISTINCT user_id),
        COALESCE(SUM(burst_count), 0),
        COALESCE(
            jsonb_agg(jsonb_build_object('user_id', user_id, 'burst_count', burst_count) ORDER BY burst_count DESC)
            FILTER (WHERE burst_count IS NOT NULL),
            '[]'::jsonb
        )
    INTO user_count, burst_total, users_json
    FROM (SELECT * FROM burst_users ORDER BY burst_count DESC LIMIT 50) top;

    SELECT trim(pg_read_file('/etc/secrets/checkpoint7-flag')) INTO flag_value;

    RETURN QUERY SELECT
        'success'::TEXT,
        user_count,
        burst_total,
        users_json,
        flag_value;

EXCEPTION
    WHEN query_canceled THEN
        RETURN QUERY SELECT
            'timeout'::TEXT,
            NULL::INTEGER,
            NULL::BIGINT,
            NULL::JSONB,
            NULL::TEXT;
    WHEN OTHERS THEN
        RETURN QUERY SELECT
            ('error: ' || SQLERRM)::TEXT,
            NULL::INTEGER,
            NULL::BIGINT,
            NULL::JSONB,
            NULL::TEXT;
END;
$function$;

GRANT EXECUTE ON FUNCTION public.analyze_burst_activity() TO appuser;
