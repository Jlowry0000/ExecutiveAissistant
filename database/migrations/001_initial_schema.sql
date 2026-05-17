-- =============================================================================
-- AI Executive Assistant - Initial Schema Migration
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- BusinessContext: Dynamic business focus and configuration
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "BusinessContext" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "core_focus" TEXT NOT NULL DEFAULT '',
    "target_keywords" JSONB NOT NULL DEFAULT '[]',
    "event_discovery_queries" JSONB NOT NULL DEFAULT '[]',
    "auto_draft_tone" TEXT NOT NULL DEFAULT 'professional',
    "default_llm_provider" TEXT NOT NULL DEFAULT 'openai',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- IMAP_Accounts: Configured email accounts for polling
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "IMAP_Accounts" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "name" TEXT NOT NULL,
    "provider" TEXT NOT NULL CHECK ("provider" IN ('gmail', 'outlook', 'custom')),
    "host" TEXT NOT NULL,
    "port" INTEGER NOT NULL DEFAULT 993,
    "username" TEXT NOT NULL,
    "encrypted_password" TEXT NOT NULL,
    "use_ssl" BOOLEAN NOT NULL DEFAULT TRUE,
    "is_active" BOOLEAN NOT NULL DEFAULT FALSE,
    "last_polled_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- FlaggedEmails: Queue of triage results
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "FlaggedEmails" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "account_id" UUID REFERENCES "IMAP_Accounts"("id") ON DELETE SET NULL,
    "message_id" TEXT NOT NULL UNIQUE,
    "sender" TEXT NOT NULL,
    "sender_name" TEXT,
    "subject" TEXT,
    "body" TEXT NOT NULL,
    "body_preview" TEXT,
    "summary" TEXT,
    "flag_reason" TEXT,
    "suggested_action" TEXT,
    "draft_response" TEXT,
    "is_flagged" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_read" BOOLEAN NOT NULL DEFAULT FALSE,
    "raw_headers" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- ActionItems: Follow-up tasks extracted from emails
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "ActionItems" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "email_id" UUID REFERENCES "FlaggedEmails"("id") ON DELETE CASCADE,
    "description" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pending' CHECK ("status" IN ('pending', 'in_progress', 'completed', 'cancelled')),
    "priority" TEXT CHECK ("priority" IN ('low', 'medium', 'high', 'urgent')),
    "due_date" DATE,
    "assigned_to" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- DigestArchive: Generated executive digests
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "DigestArchive" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "period_start" TIMESTAMPTZ NOT NULL,
    "period_end" TIMESTAMPTZ NOT NULL,
    "content_md" TEXT NOT NULL,
    "triggered_by" TEXT,
    "llm_provider" TEXT NOT NULL,
    "model_used" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- API_Keys: Authentication for webhook endpoints
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "API_Keys" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "key_hash" TEXT NOT NULL UNIQUE,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
    "last_used_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- DigestPreferences: Per-user digest settings
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "DigestPreferences" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "user_id" TEXT NOT NULL UNIQUE,
    "schedule" TEXT NOT NULL DEFAULT '0 7 * * 1-5',
    "include_calendar" BOOLEAN NOT NULL DEFAULT TRUE,
    "include_web_discovery" BOOLEAN NOT NULL DEFAULT TRUE,
    "include_flagged_emails" BOOLEAN NOT NULL DEFAULT TRUE,
    "tone" TEXT NOT NULL DEFAULT 'executive',
    "output_format" TEXT NOT NULL DEFAULT 'markdown',
    "webhook_url" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS "idx_flaggedemails_account_id" ON "FlaggedEmails"("account_id");
CREATE INDEX IF NOT EXISTS "idx_flaggedemails_is_flagged" ON "FlaggedEmails"("is_flagged");
CREATE INDEX IF NOT EXISTS "idx_flaggedemails_created_at" ON "FlaggedEmails"("created_at");
CREATE INDEX IF NOT EXISTS "idx_actionitems_email_id" ON "ActionItems"("email_id");
CREATE INDEX IF NOT EXISTS "idx_actionitems_status" ON "ActionItems"("status");
CREATE INDEX IF NOT EXISTS "idx_imap_accounts_is_active" ON "IMAP_Accounts"("is_active");
CREATE INDEX IF NOT EXISTS "idx_digestarchive_created_at" ON "DigestArchive"("created_at");

-- -----------------------------------------------------------------------------
-- Trigger: updated_at auto-update
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW."updated_at" = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_businesscontext_updated_at
    BEFORE UPDATE ON "BusinessContext"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_actionitems_updated_at
    BEFORE UPDATE ON "ActionItems"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_digestpreferences_updated_at
    BEFORE UPDATE ON "DigestPreferences"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- -----------------------------------------------------------------------------
-- Seed: Default BusinessContext (single row)
-- -----------------------------------------------------------------------------
INSERT INTO "BusinessContext" ("id", "core_focus", "target_keywords", "event_discovery_queries", "auto_draft_tone")
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Focus on revenue growth and client retention.',
    '["partnership", "enterprise deal", "renewal", "Q4", "ROI"]',
    '["tech industry trends 2024", "enterprise software acquisitions", "competitive landscape"]',
    'professional'
) ON CONFLICT DO NOTHING;

COMMIT;