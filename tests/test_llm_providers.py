import pytest
import requests
from unittest.mock import MagicMock, patch
from copilot.providers.llm.groq import GroqProvider
from copilot.providers.llm.ollama import OllamaProvider


def test_groq_configure():
    provider = GroqProvider()
    with pytest.raises(ValueError):
        provider.configure({})

    provider.configure({"api_key": "test-key", "model": "test-model"})
    assert provider.api_key == "test-key"
    assert provider.model == "test-model"


@patch("requests.post")
def test_groq_complete(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "test response"}}]
    }
    mock_post.return_value = mock_response

    provider = GroqProvider()
    provider.configure({"api_key": "test-key"})
    result = provider.complete("hello")

    assert result == "test response"
    mock_post.assert_called_once()


def test_ollama_configure():
    provider = OllamaProvider()
    provider.configure({"host": "http://other-host:11434", "model": "llama2"})
    assert provider.host == "http://other-host:11434"
    assert provider.model == "llama2"


@patch("requests.post")
def test_ollama_complete(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"content": "ollama response"}}
    mock_post.return_value = mock_response

    provider = OllamaProvider()
    result = provider.complete("hello")

    assert result == "ollama response"
    mock_post.assert_called_once()
