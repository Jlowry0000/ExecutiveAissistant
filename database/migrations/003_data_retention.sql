-- Data retention cleanup function
-- Run via: SELECT cleanup_expired_records(90);
-- Or schedule with pg_cron or a daily cron job

CREATE OR REPLACE FUNCTION cleanup_expired_records(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_total INTEGER := 0;
    deleted_count INTEGER;
BEGIN
    DELETE FROM "FlaggedEmails"
    WHERE "created_at" < NOW() - (retention_days || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    deleted_total := deleted_total + deleted_count;

    DELETE FROM "DigestArchive"
    WHERE "created_at" < NOW() - (retention_days || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    deleted_total := deleted_total + deleted_count;

    DELETE FROM "ActionItems"
    WHERE "created_at" < NOW() - (retention_days || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    deleted_total := deleted_total + deleted_count;

    RETURN deleted_total;
END;
$$ LANGUAGE plpgsql;
