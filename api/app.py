import os
import json
import hmac
import uuid
import time
import logging
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger("exec-assistant-api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from .models import (
    NocoDBClient,
    BusinessContext,
    FlaggedEmailCreate,
    FlaggedEmailsResponse,
    FlaggedEmailItem,
    DigestPayload,
    DigestTriggerResponse,
    IMAPAccountCreate,
    LLMCompleteRequest,
    LLMCompleteResponse,
    encrypt_value,
)
from src.llm_adapters import get_llm_adapter
from src.llm_adapters.validation import validate_llm_json_output, LLMValidationError


NOCODB_URL = os.environ.get("NOCODB_URL", "http://localhost:8080")
API_KEY = os.environ.get("API_KEY", "")
N8N_API_KEY = os.environ.get("N8N_API_KEY", "")
CORS_ORIGINS_RAW = os.environ.get("CORS_ORIGINS", "http://localhost:5678")
nocodb: Optional[NocoDBClient] = None

CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()]
if not CORS_ORIGINS:
    CORS_ORIGINS = ["http://localhost:5678"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global nocodb
    nocodb = NocoDBClient(NOCODB_URL, API_KEY)
    logger.info("API service started")
    yield
    await nocodb.close()
    logger.info("API service stopped")


app = FastAPI(title="AI Executive Assistant API", version="1.0.0")

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start
    logger.info(
        "request_id=%s method=%s path=%s status=%d duration=%.2fms",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration * 1000,
    )
    response.headers["X-Request-ID"] = request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["X-API-Key", "X-N8N-Key", "Content-Type", "Authorization"],
)


def _constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_n8n_key: Optional[str] = Header(None, alias="X-N8N-Key"),
) -> str:
    if x_api_key and _constant_time_compare(x_api_key, API_KEY):
        return x_api_key
    if x_n8n_key and _constant_time_compare(x_n8n_key, N8N_API_KEY):
        return x_n8n_key
    raise HTTPException(status_code=401, detail="Invalid API key")


def _get_record_id(record: dict) -> str:
    return str(record.get("Id") or record.get("id") or "")


def _parse_jsonb(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(value, list):
        return value
    return []


async def _get_or_create_context_row() -> str:
    try:
        result = await nocodb.get_rows("BusinessContext", {"limit": 1})
        rows = result.get("list", [])
        if rows:
            return _get_record_id(rows[0])
        created = await nocodb.insert_row("BusinessContext", {
            "core_focus": "",
            "target_keywords": "[]",
            "event_discovery_queries": "[]",
            "auto_draft_tone": "professional",
            "default_llm_provider": "openai",
        })
        return _get_record_id(created)
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)[:100]}")


@app.get("/context", response_model=BusinessContext)
@limiter.limit("30/minute")
async def get_context(request: Request, _: str = Depends(verify_api_key)):
    try:
        result = await nocodb.get_rows("BusinessContext", {"limit": 1})
        rows = result.get("list", [])
        if not rows:
            raise HTTPException(status_code=404, detail="BusinessContext not found")
        row = rows[0]
        return BusinessContext(
            core_focus=row.get("core_focus", ""),
            target_keywords=_parse_jsonb(row.get("target_keywords", [])),
            event_discovery_queries=_parse_jsonb(row.get("event_discovery_queries", [])),
            auto_draft_tone=row.get("auto_draft_tone", "professional"),
            default_llm_provider=row.get("default_llm_provider", "openai"),
        )
    except HTTPException:
        raise
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)[:100]}")


@app.put("/context", response_model=BusinessContext)
@limiter.limit("10/minute")
async def put_context(
    request: Request,
    ctx: BusinessContext,
    _: str = Depends(verify_api_key)
):
    try:
        row_id = await _get_or_create_context_row()
        await nocodb.update_row("BusinessContext", row_id, {
            "core_focus": ctx.core_focus,
            "target_keywords": json.dumps(ctx.target_keywords),
            "event_discovery_queries": json.dumps(ctx.event_discovery_queries),
            "auto_draft_tone": ctx.auto_draft_tone,
            "default_llm_provider": ctx.default_llm_provider,
        })
        return ctx
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)[:100]}")


@app.post("/correspondence/flagged", response_model=FlaggedEmailItem)
@limiter.limit("30/minute")
async def post_flagged_email(
    request: Request,
    email: FlaggedEmailCreate,
    _: str = Depends(verify_api_key)
):
    try:
        existing = await nocodb.get_rows("FlaggedEmails", {
            "where": f"(message_id,eq,{email.message_id})",
            "limit": 1,
        })
        existing_rows = existing.get("list", [])
        if existing_rows:
            row = existing_rows[0]
            return FlaggedEmailItem(
                id=_get_record_id(row),
                sender=row.get("sender", email.sender),
                sender_name=row.get("sender_name"),
                subject=row.get("subject"),
                summary=row.get("summary"),
                flag_reason=row.get("flag_reason"),
                suggested_action=row.get("suggested_action"),
                draft_response=row.get("draft_response"),
                is_flagged=row.get("is_flagged", False),
                created_at=row.get("created_at", ""),
            )

        created = await nocodb.insert_row("FlaggedEmails", email.model_dump())
        return FlaggedEmailItem(
            id=_get_record_id(created),
            sender=email.sender,
            sender_name=email.sender_name,
            subject=email.subject,
            summary=email.summary,
            flag_reason=email.flag_reason,
            suggested_action=email.suggested_action,
            draft_response=email.draft_response,
            is_flagged=email.is_flagged,
            created_at=created.get("created_at", ""),
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise HTTPException(status_code=409, detail="Duplicate email (message_id conflict)")
        raise HTTPException(status_code=502, detail=f"Storage error: {str(e)[:100]}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)[:100]}")


@app.get("/correspondence/flagged", response_model=FlaggedEmailsResponse)
@limiter.limit("30/minute")
async def get_flagged_emails(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    _: str = Depends(verify_api_key)
):
    try:
        result = await nocodb.get_rows("FlaggedEmails", {
            "where": "(is_flagged,eq,true)",
            "limit": limit,
            "offset": offset,
            "sort": "-created_at",
        })
        rows = result.get("list", [])
        page_info = result.get("pageInfo", {})
        items = [
            FlaggedEmailItem(
                id=_get_record_id(r),
                sender=r["sender"],
                sender_name=r.get("sender_name"),
                subject=r.get("subject"),
                summary=r.get("summary"),
                flag_reason=r.get("flag_reason"),
                suggested_action=r.get("suggested_action"),
                draft_response=r.get("draft_response"),
                is_flagged=r.get("is_flagged", False),
                created_at=r.get("created_at"),
            )
            for r in rows
        ]
        total = page_info.get("totalRows", len(items))
        return FlaggedEmailsResponse(data=items, count=len(items), total=total)
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)[:100]}")


@app.post("/digest/trigger", response_model=DigestTriggerResponse)
@limiter.limit("10/minute")
async def trigger_digest(
    request: Request,
    payload: DigestPayload,
    _: str = Depends(verify_api_key)
):
    try:
        created = await nocodb.insert_row("DigestArchive", payload.model_dump())
        return DigestTriggerResponse(
            status="accepted",
            message="Digest saved successfully.",
            digest_id=_get_record_id(created),
        )
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)[:100]}")


@app.post("/imap-accounts")
@limiter.limit("10/minute")
async def create_imap_account(
    request: Request,
    account: IMAPAccountCreate,
    _: str = Depends(verify_api_key)
):
    try:
        data = account.model_dump()
        data["encrypted_password"] = encrypt_value(data.pop("password"))
        created = await nocodb.insert_row("IMAP_Accounts", data)
        return {"id": _get_record_id(created), "name": account.name, "status": "created"}
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)[:100]}")


@app.post("/llm/complete", response_model=LLMCompleteResponse)
@limiter.limit("30/minute")
async def llm_complete(
    request: Request,
    req: LLMCompleteRequest,
    _: str = Depends(verify_api_key)
):
    provider_name = req.provider
    model = req.model
    api_key = os.environ.get(f"{provider_name.upper()}_API_KEY")
    base_url = os.environ.get(f"{provider_name.upper()}_BASE_URL")

    try:
        adapter = get_llm_adapter(
            provider=provider_name,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        content = adapter.complete(
            messages=req.messages,
            json_output=req.json_output,
            temperature=req.temperature,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code >= 500:
            raise HTTPException(status_code=502, detail=f"LLM provider error: {str(e)[:100]}")
        raise HTTPException(status_code=400, detail=f"LLM request rejected: {str(e)[:100]}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="LLM provider timed out")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {str(e)[:100]}")

    if req.json_output:
        try:
            validate_llm_json_output(content)
        except LLMValidationError as e:
            raise HTTPException(status_code=502, detail=f"LLM returned invalid output: {str(e)[:100]}")

    return LLMCompleteResponse(
        content=content,
        provider=adapter.provider_name,
        model=adapter.model,
    )


@app.get("/imap-accounts")
@limiter.limit("30/minute")
async def list_imap_accounts(
    request: Request,
    _: str = Depends(verify_api_key)
):
    try:
        result = await nocodb.get_rows("IMAP_Accounts", {"limit": 100})
        rows = result.get("list", [])
        accounts = []
        for r in rows:
            accounts.append({
                "id": _get_record_id(r),
                "name": r.get("name"),
                "provider": r.get("provider"),
                "host": r.get("host"),
                "port": r.get("port"),
                "username": r.get("username"),
                "use_ssl": r.get("use_ssl", True),
                "is_active": r.get("is_active", False),
                "last_polled_at": r.get("last_polled_at"),
            })
        return {"data": accounts, "count": len(accounts)}
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)[:100]}")


@app.get("/health")
@limiter.limit("120/minute")
async def health(request: Request):
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
