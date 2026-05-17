import os
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional

from .models import (
    NocoDBClient,
    APIKeyAuth,
    BusinessContext,
    FlaggedEmailsResponse,
    FlaggedEmailItem,
    DigestTriggerResponse,
)


NOCODB_URL = os.environ.get("NOCODB_URL", "http://localhost:8080")
API_KEY = os.environ.get("API_KEY", "")
nocodb: Optional[NocoDBClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global nocodb
    nocodb = NocoDBClient(NOCODB_URL, API_KEY)
    yield
    await nocodb.close()


app = FastAPI(title="AI Executive Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@app.get("/context", response_model=BusinessContext)
async def get_context(_: str = Depends(verify_api_key)):
    result = await nocodb.get_rows("BusinessContext", {"limit": 1})
    rows = result.get("list", [])
    if not rows:
        raise HTTPException(status_code=404, detail="BusinessContext not found")
    row = rows[0]
    return BusinessContext(
        core_focus=row.get("core_focus", ""),
        target_keywords=row.get("target_keywords", []),
        event_discovery_queries=row.get("event_discovery_queries", []),
        auto_draft_tone=row.get("auto_draft_tone", "professional"),
        default_llm_provider=row.get("default_llm_provider", "openai"),
    )


@app.put("/context", response_model=BusinessContext)
async def put_context(
    ctx: BusinessContext,
    _: str = Depends(verify_api_key)
):
    await nocodb.update_row("BusinessContext", "00000000-0000-0000-0000-000000000001", {
        "core_focus": ctx.core_focus,
        "target_keywords": ctx.target_keywords,
        "event_discovery_queries": ctx.event_discovery_queries,
        "auto_draft_tone": ctx.auto_draft_tone,
        "default_llm_provider": ctx.default_llm_provider,
    })
    return ctx


@app.get("/correspondence/flagged", response_model=FlaggedEmailsResponse)
async def get_flagged_emails(
    limit: int = 50,
    offset: int = 0,
    _: str = Depends(verify_api_key)
):
    result = await nocodb.get_rows("FlaggedEmails", {
        "where": "(is_flagged,eq,true)",
        "limit": limit,
        "offset": offset,
        "sort": "-created_at",
    })
    rows = result.get("list", [])
    items = [
        FlaggedEmailItem(
            id=r["Id"],
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
    return FlaggedEmailsResponse(data=items, count=len(items))


@app.post("/digest/trigger", response_model=DigestTriggerResponse)
async def trigger_digest(_: str = Depends(verify_api_key)):
    return DigestTriggerResponse(
        status="accepted",
        message="Digest generation has been queued.",
        digest_id=None,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)