from pydantic import BaseModel
from typing import Optional
import httpx


class BusinessContext(BaseModel):
    core_focus: str = ""
    target_keywords: list[str] = []
    event_discovery_queries: list[str] = []
    auto_draft_tone: str = "professional"
    default_llm_provider: str = "openai"


class FlaggedEmailItem(BaseModel):
    id: str
    sender: str
    sender_name: Optional[str]
    subject: Optional[str]
    summary: Optional[str]
    flag_reason: Optional[str]
    suggested_action: Optional[str]
    draft_response: Optional[str]
    is_flagged: bool
    created_at: str


class FlaggedEmailsResponse(BaseModel):
    data: list[FlaggedEmailItem]
    count: int


class DigestTriggerResponse(BaseModel):
    status: str
    message: str
    digest_id: Optional[str] = None


class APIKeyAuth:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def verify(self, key: str) -> bool:
        return key == self.api_key


class NocoDBClient:
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self._http = httpx.AsyncClient(timeout=30.0)

    async def get_rows(self, table: str, params: dict | None = None) -> dict:
        headers = {"xc-token": self.api_key} if self.api_key else {}
        resp = await self._http.get(
            f"{self.base_url}/api/v1/db/data/v1/exec_assistant/{table}",
            headers=headers,
            params=params or {}
        )
        resp.raise_for_status()
        return resp.json()

    async def update_row(self, table: str, row_id: str, data: dict) -> dict:
        headers = {"xc-token": self.api_key} if self.api_key else {}
        resp = await self._http.patch(
            f"{self.base_url}/api/v1/db/data/v1/exec_assistant/{table}/{row_id}",
            headers=headers,
            json=data
        )
        resp.raise_for_status()
        return resp.json()

    async def insert_row(self, table: str, data: dict) -> dict:
        headers = {"xc-token": self.api_key} if self.api_key else {}
        resp = await self._http.post(
            f"{self.base_url}/api/v1/db/data/v1/exec_assistant/{table}",
            headers=headers,
            json=data
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self._http.aclose()