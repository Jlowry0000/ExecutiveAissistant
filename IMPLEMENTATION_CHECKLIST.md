# AI Executive Assistant - Implementation Checklist

## Getting Started

- [ ] Copy `.env.example` to `.env` and fill in all credentials
- [ ] Ensure Docker and Docker Compose are installed
- [ ] Review the architecture document (`/home/jordan/Downloads/AI Executive Assistant - Architecture & n8n Spec.md`)

## Phase 1: Infrastructure
- [x] Created `docker-compose.yml` with PostgreSQL, NocoDB, n8n, and API services
- [x] Created `.env.example` with all environment variables
- [x] Created `.gitignore`

**Verify:** Run `docker-compose config` to validate the compose file.

## Phase 2: Database
- [x] Created `database/migrations/001_initial_schema.sql`
- [x] Created `database/nocodb/SETUP.md` with manual setup instructions
- [x] Created `database/nocodb/import_project.py` for programmatic NocoDB setup

**Verify:** 
```bash
docker-compose up -d postgres
# Wait for postgres to be healthy
docker-compose exec postgres psql -U exec_assistant -d exec_assistant -f / migrations/001_initial_schema.sql
```

## Phase 3: LLM Adapters
- [x] Created `src/llm_adapters/base.py`
- [x] Created `src/llm_adapters/openai.py`
- [x] Created `src/llm_adapters/ollama.py`
- [x] Created `src/llm_adapters/minimax.py`
- [x] Created `src/llm_adapters/deepseek.py`
- [x] Created `src/llm_adapters/__init__.py` (factory)
- [x] Created `src/config.py`

**Verify:**
```bash
cd /home/jordan/Projects/ExecutiveAissistant
pip install httpx pydantic python-dotenv
python -c "from src.llm_adapters import get_llm_adapter; print(get_llm_adapter('openai', api_key='test').provider_name)"
```

## Phase 4: FastAPI Webhook Service
- [x] Created `api/models.py`
- [x] Created `api/app.py`
- [x] Created `api/requirements.txt`
- [x] Created `api/Dockerfile` (proper container build, replaces inline pip)

**Verify:**
```bash
cd /home/jordan/Projects/ExecutiveAissistant
docker-compose build api
docker-compose run --rm api python -c "from app import app; print('FastAPI app loaded OK')"
```

## Phase 5: n8n Workflows
- [x] Created `n8n/workflows/01-email-triage.json`
- [x] Created `n8n/workflows/02-digest-compiler.json`

**Verify:** Import both JSON files into your n8n instance via the UI.

## Phase 6: Testing
- [x] Created `tests/test_llm_adapters.py`
- [x] Created `tests/test_api.py`

**Run tests:**
```bash
cd /home/jordan/Projects/ExecutiveAissistant
python3 -m venv .venv
.venv/bin/pip install -r api/requirements.txt pytest
.venv/bin/pytest tests/ -v
```

## Deployment Steps

1. **Start the stack:**
   ```bash
   docker-compose up -d
   ```

2. **Initialize the database:**
   ```bash
   docker-compose exec postgres psql -U exec_assistant -d exec_assistant -f /migrations/001_initial_schema.sql
   ```

3. **Import NocoDB project** (optional, or use UI):
   ```bash
   docker-compose up -d nocodb
   # Then follow SETUP.md instructions
   ```

4. **Configure IMAP credentials in NocoDB:**
   - Go to NocoDB UI → `IMAP_Accounts` table
   - Add your Gmail/Outlook/custom account(s)
   - For Gmail: Use an [App Password](https://support.google.com/accounts/answer/185833)
   - For Outlook: Use an [App Password](https://support.microsoft.com/en-us/account-billing/manage-app-passwords-for-two-step-verification-58929116-73e1-4f95-b2ce-86bb9b1871f7)

5. **Import n8n workflows:**
   - Open n8n at http://localhost:5678
   - Import `n8n/workflows/01-email-triage.json`
   - Import `n8n/workflows/02-digest-compiler.json`
   - Configure n8n credentials for IMAP and LLM
   - Ensure `N8N_API_KEY` env var is set (must match `API_KEY` in `.env`)

6. **Update BusinessContext:**
   - Use the API or NocoDB UI to set your `core_focus` and `target_keywords`
   ```bash
   curl -X PUT http://localhost:8000/context \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"core_focus": "Your business focus here", "target_keywords": ["keyword1", "keyword2"]}'
   ```

## Multi-IMAP Setup

To add multiple email accounts:
1. Add entries to `IMAP_ACCOUNTS` env var (JSON array)
2. Configure each in NocoDB `IMAP_Accounts` table
3. In the n8n workflow, use a "Split In Batches" node to iterate over each active account

## Switching LLM Providers

The Python LLM adapter layer (`src/llm_adapters/`) supports all four providers via `get_llm_adapter()`. However, the n8n workflows currently call OpenAI's API directly, so switching requires editing the workflow's HTTP Request node:

**In n8n LLM node:**
- Change the URL to your provider's chat completions endpoint
- Update the `Authorization` header and `model` parameter
- Adjust the request/response parsing in the downstream Code node

**The `DEFAULT_LLM_PROVIDER` env var** controls which adapter the Python API code uses for server-side LLM operations (future endpoints only).

## Architecture Notes

- **Triage Pipeline (Pipeline A):** Triggered every 5 minutes by IMAP scheduler. Fetches new emails, runs them through LLM with BusinessContext, stores results in NocoDB.
- **Digest Pipeline (Pipeline B):** Runs weekdays at 7 AM (configurable via CRON). Fetches flagged emails, synthesizes into Markdown digest, saves to NocoDB and optionally emails.
- **State Store:** NocoDB connects to PostgreSQL. All tables are accessible via both NocoDB UI and direct API calls.
- **LLM Abstraction:** Four providers supported. Factory function `get_llm_adapter(provider)` returns the appropriate adapter. Each adapter implements `complete(messages, json_output=False)`.