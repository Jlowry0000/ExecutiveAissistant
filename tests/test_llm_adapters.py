import pytest
from unittest.mock import patch, MagicMock


class TestLLMAdapters:
    def test_openai_adapter_import(self):
        from src.llm_adapters.openai import OpenAIAdapter
        adapter = OpenAIAdapter(api_key="test-key", model="gpt-4o")
        assert adapter.provider_name == "openai"
        assert adapter.model == "gpt-4o"
        assert adapter.api_key == "test-key"

    def test_ollama_adapter_import(self):
        from src.llm_adapters.ollama import OllamaAdapter
        adapter = OllamaAdapter(base_url="http://localhost:11434", model="llama3.2")
        assert adapter.provider_name == "ollama"
        assert adapter.model == "llama3.2"

    def test_minimax_adapter_import(self):
        from src.llm_adapters.minimax import MiniMaxAdapter
        adapter = MiniMaxAdapter(api_key="test-key", model="abab6-chat")
        assert adapter.provider_name == "minimax"
        assert adapter.model == "abab6-chat"

    def test_deepseek_adapter_import(self):
        from src.llm_adapters.deepseek import DeepSeekAdapter
        adapter = DeepSeekAdapter(api_key="test-key", model="deepseek-chat")
        assert adapter.provider_name == "deepseek"
        assert adapter.model == "deepseek-chat"

    @patch("httpx.post")
    def test_openai_complete(self, mock_post):
        from src.llm_adapters.openai import OpenAIAdapter
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_post.return_value = mock_response

        adapter = OpenAIAdapter(api_key="test-key")
        result = adapter.complete([{"role": "user", "content": "Hello"}])
        assert result == "Test response"
        mock_post.assert_called_once()

    @patch("httpx.post")
    def test_openai_complete_json_output(self, mock_post):
        from src.llm_adapters.openai import OpenAIAdapter
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"is_flagged": true}'}}]
        }
        mock_post.return_value = mock_response

        adapter = OpenAIAdapter(api_key="test-key")
        result = adapter.complete([{"role": "user", "content": "Hello"}], json_output=True)
        assert result == '{"is_flagged": true}'
        call_kwargs = mock_post.call_args[1]["json"]
        assert call_kwargs["response_format"] == {"type": "json_object"}


class TestAdapterFactory:
    def test_get_llm_adapter_openai(self):
        from src.llm_adapters import get_llm_adapter
        adapter = get_llm_adapter("openai", api_key="test")
        assert adapter.provider_name == "openai"

    def test_get_llm_adapter_ollama(self):
        from src.llm_adapters import get_llm_adapter
        adapter = get_llm_adapter("ollama")
        assert adapter.provider_name == "ollama"

    def test_get_llm_adapter_unknown(self):
        from src.llm_adapters import get_llm_adapter
        with pytest.raises(ValueError) as exc_info:
            get_llm_adapter("unknown_provider")
        assert "unknown_provider" in str(exc_info.value)
        assert "Available" in str(exc_info.value)


class TestConfig:
    def test_config_from_env(self):
        import os
        with patch.dict(os.environ, {
            "POSTGRES_HOST": "db.example.com",
            "POSTGRES_DB": "test_db",
            "OPENAI_API_KEY": "sk-test",
            "MINIMAX_API_KEY": "minimax-test",
        }):
            from src.config import AppConfig
            config = AppConfig.from_env()
            assert config.postgres_host == "db.example.com"
            assert config.postgres_db == "test_db"
            assert config.llm_configs["openai"].api_key == "sk-test"
            assert config.llm_configs["minimax"].api_key == "minimax-test"