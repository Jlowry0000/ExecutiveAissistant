import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    provider: str = "openai"
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None


@dataclass
class IMAPAccount:
    name: str
    provider: str
    host: str
    port: int
    username: str
    password: str
    is_active: bool = False
    use_ssl: bool = True


@dataclass
class AppConfig:
    postgres_host: str = "localhost"
    postgres_db: str = "exec_assistant"
    postgres_user: str = "exec_assistant"
    postgres_password: str = ""

    nocodb_url: str = "http://localhost:8080"
    nocodb_api_key: Optional[str] = None

    api_key: str = ""

    n8n_url: str = "http://localhost:5678"

    default_llm_provider: str = "openai"
    llm_configs: dict[str, LLMConfig] = field(default_factory=dict)

    imap_accounts: list[IMAPAccount] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "AppConfig":
        config = cls()
        config.postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
        config.postgres_db = os.environ.get("POSTGRES_DB", "exec_assistant")
        config.postgres_user = os.environ.get("POSTGRES_USER", "exec_assistant")
        config.postgres_password = os.environ.get("POSTGRES_PASSWORD", "")
        config.nocodb_url = os.environ.get("NOCODB_URL", "http://localhost:8080")
        config.nocodb_api_key = os.environ.get("NOCODB_API_KEY")
        config.api_key = os.environ.get("API_KEY", "")
        config.n8n_url = os.environ.get("N8N_URL", "http://localhost:5678")
        config.default_llm_provider = os.environ.get("DEFAULT_LLM_PROVIDER", "openai")

        config.llm_configs = {
            "openai": LLMConfig(
                provider="openai",
                api_key=os.environ.get("OPENAI_API_KEY"),
                model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            ),
            "ollama": LLMConfig(
                provider="ollama",
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                model=os.environ.get("OLLAMA_MODEL", "llama3.2"),
            ),
            "minimax": LLMConfig(
                provider="minimax",
                api_key=os.environ.get("MINIMAX_API_KEY"),
                model=os.environ.get("MINIMAX_MODEL", "abab6-chat"),
                base_url=os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.chat/v1"),
            ),
            "deepseek": LLMConfig(
                provider="deepseek",
                api_key=os.environ.get("DEEPSEEK_API_KEY"),
                model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            ),
        }

        import json
        imap_json = os.environ.get("IMAP_ACCOUNTS", "[]")
        try:
            accounts_data = json.loads(imap_json)
            config.imap_accounts = [
                IMAPAccount(
                    name=a.get("name", ""),
                    provider=a.get("provider", "custom"),
                    host=a.get("host", ""),
                    port=a.get("port", 993),
                    username=a.get("username", ""),
                    password=a.get("password", ""),
                    is_active=a.get("is_active", False),
                    use_ssl=a.get("use_ssl", True),
                )
                for a in accounts_data
            ]
        except json.JSONDecodeError:
            pass

        return config