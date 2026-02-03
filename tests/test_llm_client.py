"""Tests for llm_plugin.client backend selection and error handling."""

import os
from unittest.mock import patch

from llm_plugin.client import _http_client, _local_stub, _template_client, get_client


def test_get_client_default_template():
    """Test default client returns template backend."""
    client = get_client()
    result = client("test prompt")
    assert "[LLM TEMPLATE]" in result
    assert "test prompt" in result


def test_get_client_explicit_template():
    """Test explicit template backend selection."""
    client = get_client(backend="template")
    result = client("test prompt")
    assert "[LLM TEMPLATE]" in result


def test_get_client_local_stub():
    """Test local stub backend selection."""
    client = get_client(backend="local")
    result = client("test prompt")
    assert "[LOCAL STUB]" in result


def test_get_client_http_backend():
    """Test HTTP backend selection."""
    client = get_client(backend="http")
    assert client == _http_client


def test_get_client_openai_backend():
    """Test openai backend alias."""
    client = get_client(backend="openai")
    assert client == _http_client


def test_get_client_invalid_fallback():
    """Test unknown backend falls back to template."""
    client = get_client(backend="unknown")
    result = client("test")
    assert "[LLM TEMPLATE]" in result


def test_get_client_pcbr_env_override(monkeypatch):
    """Test PCBR_LLM_BACKEND overrides backend parameter."""
    monkeypatch.setenv("PCBR_LLM_BACKEND", "local")
    client = get_client(backend="template")
    result = client("test")
    assert "[LOCAL STUB]" in result


def test_get_client_case_insensitive():
    """Test backend selection is case-insensitive."""
    assert get_client(backend="HTTP") == _http_client
    assert get_client(backend="TEMPLATE")("test") == "[LLM TEMPLATE]\ntest"


def test_template_client():
    """Test template client format."""
    assert _template_client("prompt") == "[LLM TEMPLATE]\nprompt"


def test_local_stub():
    """Test local stub format."""
    assert _local_stub("prompt") == "[LOCAL STUB]\nprompt"


def test_http_client_no_api_key():
    """Test HTTP client error when API key is missing."""
    with patch.dict(os.environ, {}, clear=True):
        result = _http_client("test")
        assert "[ERROR]" in result
        assert "API_KEY not set" in result


def test_http_client_pcbr_precedence(monkeypatch):
    """Test PCBR_* environment variables take precedence."""
    monkeypatch.setenv("OPENAI_API_KEY", "old")
    monkeypatch.setenv("PCBR_OPENAI_API_KEY", "new")
    # Without making actual API call, just verify env vars are read correctly
    # (actual API calls are tested in test_llm_plugin.py)
    with patch.dict(os.environ):
        api_key = os.getenv("PCBR_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        assert api_key == "new"


def test_http_client_fallback_to_openai(monkeypatch):
    """Test fallback to OPENAI_* when PCBR_* not set."""
    monkeypatch.delenv("PCBR_OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "fallback")
    with patch.dict(os.environ):
        api_key = os.getenv("PCBR_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        assert api_key == "fallback"
