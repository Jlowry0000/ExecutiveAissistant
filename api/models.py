import os
import base64
from pydantic import BaseModel
from typing import Optional
import httpx
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _get_fernet() -> Fernet:
    key = os.environ.get("ENCRYPTION_KEY", "")
    if not key:
        raise ValueError("ENCRYPTION_KEY is not set")
    key_bytes = base64.urlsafe_b64decode(key.encode())
    return Fernet(key_bytes)


def encrypt_value(plaintext: str) -> str:
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()


class IMAPAccountCreate(BaseModel):
    name: str
    provider: str = "custom"
    host: str
    port: int = 993
    username: str
    password: str
    is_active: bool = False
    use_ssl: bool = True


class BusinessContext(BaseModel):
    core_focus: str = ""
    target_keywords: list[str] = []
    event_discovery_queries: list[str] = []
    auto_draft_tone: str = "professional"
    default_llm_provider: str = "openai"


class FlaggedEmailCreate(BaseModel):
    message_id: str
    sender: str
    sender_name: Optional[str] = None
    subject: Optional[str] = None
    body: str = ""
    body_preview: Optional[str] = None
    summary: Optional[str] = None
    flag_reason: Optional[str] = None
    suggested_action: Optional[str] = None
    draft_response: Optional[str] = None
    is_flagged: bool = False
    is_read: bool = True


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
    total: int = 0


class DigestPayload(BaseModel):
    content_md: str
    period_start: str
    period_end: str
    llm_provider: str
    model_used: Optional[str] = None
    triggered_by: Optional[str] = None


class DigestTriggerResponse(BaseModel):
    status: str
    message: str
    digest_id: Optional[str] = None


class LLMCompleteRequest(BaseModel):
    provider: str = "openai"
    messages: list[dict[str, str]]
    json_output: bool = False
    temperature: float = 0.2
    model: Optional[str] = None


class LLMCompleteResponse(BaseModel):
    content: str
    provider: str
    model: str


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