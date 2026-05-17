# NocoDB Setup Guide

Since NocoDB project exports are UI-driven, follow these steps to pre-configure your tables:

## Manual Setup via NocoDB UI

1. Start the stack: `docker-compose up -d`
2. Open http://localhost:8080 in your browser
3. Sign up / sign in as admin
4. Create a new **Project** → Connect your **PostgreSQL** database:
   - Host: `postgres`
   - Port: `5432`
   - Database: `exec_assistant`
   - Username: `exec_assistant`
   - Password: (from your `.env`)

5. Create the following tables (columns as defined in `../migrations/001_initial_schema.sql`):

### Table: `BusinessContext`
| Column | Type | Options |
|--------|------|---------|
| id | UUID | Primary Key, Default: gen_random_uuid() |
| core_focus | Text | Required, Default: '' |
| target_keywords | JSON | Required, Default: '[]' |
| event_discovery_queries | JSON | Required, Default: '[]' |
| auto_draft_tone | Text | Required, Default: 'professional' |
| default_llm_provider | Text | Required, Default: 'openai' |
| created_at | DateTime | Default: NOW() |
| updated_at | DateTime | Default: NOW() |

### Table: `IMAP_Accounts`
| Column | Type | Options |
|--------|------|---------|
| id | UUID | Primary Key |
| name | Text | Required |
| provider | Text | Required, Options: gmail/outlook/custom |
| host | Text | Required |
| port | Integer | Required, Default: 993 |
| username | Text | Required |
| encrypted_password | Text | Required |
| use_ssl | Boolean | Default: true |
| is_active | Boolean | Default: false |
| last_polled_at | DateTime | |
| created_at | DateTime | Default: NOW() |

### Table: `FlaggedEmails`
| Column | Type | Options |
|--------|------|---------|
| id | UUID | Primary Key |
| account_id | UUID | FK → IMAP_Accounts |
| message_id | Text | Unique, Required |
| sender | Text | Required |
| sender_name | Text | |
| subject | Text | |
| body | LongText | Required |
| body_preview | Text | |
| summary | Text | |
| flag_reason | Text | |
| suggested_action | Text | |
| draft_response | LongText | |
| is_flagged | Boolean | Default: false |
| is_read | Boolean | Default: false |
| raw_headers | JSON | |
| created_at | DateTime | Default: NOW() |

### Table: `ActionItems`
| Column | Type | Options |
|--------|------|---------|
| id | UUID | Primary Key |
| email_id | UUID | FK → FlaggedEmails (Cascade) |
| description | Text | Required |
| status | Text | Options: pending/in_progress/completed/cancelled |
| priority | Text | Options: low/medium/high/urgent |
| due_date | Date | |
| assigned_to | Text | |
| created_at | DateTime | Default: NOW() |
| updated_at | DateTime | Default: NOW() |

### Table: `DigestArchive`
| Column | Type | Options |
|--------|------|---------|
| id | UUID | Primary Key |
| period_start | DateTime | Required |
| period_end | DateTime | Required |
| content_md | LongText | Required |
| triggered_by | Text | |
| llm_provider | Text | Required |
| model_used | Text | |
| created_at | DateTime | Default: NOW() |

### Table: `API_Keys`
| Column | Type | Options |
|--------|------|---------|
| id | UUID | Primary Key |
| key_hash | Text | Unique, Required |
| name | Text | Required |
| description | Text | |
| is_active | Boolean | Default: true |
| last_used_at | DateTime | |
| created_at | DateTime | Default: NOW() |

### Table: `DigestPreferences`
| Column | Type | Options |
|--------|------|---------|
| id | UUID | Primary Key |
| user_id | Text | Unique, Required |
| schedule | Text | Default: '0 7 * * 1-5' |
| include_calendar | Boolean | Default: true |
| include_web_discovery | Boolean | Default: true |
| include_flagged_emails | Boolean | Default: true |
| tone | Text | Default: 'executive' |
| output_format | Text | Default: 'markdown' |
| webhook_url | Text | |
| created_at | DateTime | Default: NOW() |
| updated_at | DateTime | Default: NOW() |

## Auto-Setup via SQL Migration

The `../migrations/001_initial_schema.sql` file can be run directly on PostgreSQL:

```bash
PGPASSWORD=your_password psql -h localhost -U exec_assistant -d exec_assistant -f ../migrations/001_initial_schema.sql
```

NocoDB will automatically pick up the existing PostgreSQL tables as new tables/projects.

## Post-Setup

After creating tables, you can optionally:
1. Create **Views** in NocoDB for common queries (e.g., "Today's Flagged Emails", "Pending Action Items")
2. Set up **Row-level security** if needed
3. Configure **API tokens** in NocoDB for programmatic access