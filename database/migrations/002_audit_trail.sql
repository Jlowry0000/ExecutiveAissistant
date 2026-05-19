BEGIN;

CREATE TABLE IF NOT EXISTS "AuditLog" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "request_id" TEXT,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "method" TEXT NOT NULL,
    "path" TEXT NOT NULL,
    "status_code" INTEGER NOT NULL,
    "duration_ms" INTEGER,
    "actor" TEXT,
    "ip_address" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS "idx_auditlog_timestamp" ON "AuditLog"("timestamp");
CREATE INDEX IF NOT EXISTS "idx_auditlog_actor" ON "AuditLog"("actor");

COMMIT;
