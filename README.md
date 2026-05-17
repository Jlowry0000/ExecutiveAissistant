# AI Executive Assistant

A self-hosted AI executive assistant that triages emails and generates contextual business digests, built with n8n, PostgreSQL, NocoDB, and a multi-provider LLM abstraction layer.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AI Executive Assistant                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐     ┌──────────────────┐     ┌────────────────┐  │
│  │   n8n        │     │   FastAPI        │     │   NocoDB       │  │
│  │  Orchestration│◄──►│   Webhook API    │◄──►│   + PostgreSQL │  │
│  │  (Workflows) │     │   (Endpoints)    │     │   (State Store)│  │
│  └──────┬───────┘     └──────────────────┘     └────────┬───────┘  │
│         │                                                │           │
│         │              ┌──────────────────┐              │           │
│         └────────────►│   LLM Adapters   │◄─────────────┘           │
│                        │ OpenAI / Ollama  │                           │
│                        │ MiniMax / DeepSeek                         │
│                        └──────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

- **Email Triage (Pipeline A):** IMAP polling → LLM analysis → JSON categorization → NocoDB storage
- **Executive Digests (Pipeline B):** Scheduled synthesis of flagged emails into Markdown briefings
- **Multi-Provider LLM:** OpenAI, Ollama (local), MiniMax, DeepSeek — switch via config
- **Multi-IMAP:** Support for Gmail, Outlook, and custom IMAP servers simultaneously
- **REST API:** Exposes `/context`, `/correspondence/flagged`, `/digest/trigger` endpoints

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Infrastructure

```bash
docker-compose up -d
```

### 3. Initialize Database

```bash
docker-compose exec postgres psql -U exec_assistant -d exec_assistant -f /migrations/001_initial_schema.sql
```

### 4. Import n8n Workflows

Open n8n at http://localhost:5678 and import:
- `n8n/workflows/01-email-triage.json`
- `n8n/workflows/02-digest-compiler.json`

### 5. Configure Business Context

```bash
curl -X PUT http://localhost:8000/context \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "core_focus": "Revenue growth and enterprise deals",
    "target_keywords": ["partnership", "enterprise", "renewal"],
    "auto_draft_tone": "professional"
  }'
```

## Project Structure

```
ExecutiveAissistant/
├── docker-compose.yml          # All services
├── .env.example                # Environment template
├── n8n/workflows/
│   ├── 01-email-triage.json    # Pipeline A
│   └── 02-digest-compiler.json  # Pipeline B
├── database/
│   ├── migrations/             # SQL schema
│   └── nocodb/                 # NocoDB setup docs
├── src/
│   ├── llm_adapters/           # Multi-provider LLM
│   └── config.py               # Config loader
├── api/
│   ├── app.py                  # FastAPI endpoints
│   ├── models.py              # Pydantic models
│   └── requirements.txt
└── tests/                      # Unit tests
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/context` | Retrieve current BusinessContext |
| PUT | `/context` | Update BusinessContext |
| GET | `/correspondence/flagged` | List flagged emails |
| POST | `/digest/trigger` | Trigger digest generation |
| GET | `/health` | Health check |

All endpoints require `X-API-Key` header.

## LLM Providers

The system supports four LLM providers. Set `DEFAULT_LLM_PROVIDER` in `.env`:

| Provider | Model Default | Notes |
|----------|--------------|-------|
| `openai` | gpt-4o | Requires `OPENAI_API_KEY` |
| `ollama` | llama3.2 | Local, set `OLLAMA_BASE_URL` |
| `minimax` | abab6-chat | Requires `MINIMAX_API_KEY` |
| `deepseek` | deepseek-chat | Requires `DEEPSEEK_API_KEY` |

## Documentation

- [Implementation Checklist](IMPLEMENTATION_CHECKLIST.md) — Detailed setup and verification steps
- [NocoDB Setup Guide](database/nocodb/SETUP.md) — Table and view configuration