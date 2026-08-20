from unittest.mock import patch, MagicMock
import pytest
import requests
from src.services.generation import AnswerGenerator, GenerationError

def test_generate_with_no_chunks_returns_fallback():
    generator = AnswerGenerator()
    answer = generator.generate("What is X?", [])
    assert "No relevant context" in answer

def test_generate_calls_ollama_and_returns_response():
    generator = AnswerGenerator()
    chunks = [{"chunk_id": 1, "source": "arxiv", "text": "The sky is blue."}]

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "The sky is blue [Source 1]."}
    mock_resp.raise_for_status.return_value = None

    with patch("src.services.generation.requests.post", return_value=mock_resp) as mock_post:
        answer = generator.generate("What color is the sky?", chunks)

    assert answer == "The sky is blue [Source 1]."
    called_json = mock_post.call_args.kwargs["json"]
    assert "The sky is blue." in called_json["prompt"]
    assert "What color is the sky?" in called_json["prompt"]
    assert called_json["options"]["num_predict"] == -1

def test_generate_respects_per_call_num_predict_override():
    generator = AnswerGenerator(num_predict=-1)
    chunks = [{"chunk_id": 1, "source": "arxiv", "text": "some text"}]

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "short answer"}
    mock_resp.raise_for_status.return_value = None

    with patch("src.services.generation.requests.post", return_value=mock_resp) as mock_post:
        generator.generate("question", chunks, num_predict=64)

    assert mock_post.call_args.kwargs["json"]["options"]["num_predict"] == 64

def test_generate_raises_on_request_failure():
    generator = AnswerGenerator()
    chunks = [{"chunk_id": 1, "source": "arxiv", "text": "some text"}]

    with patch("src.services.generation.requests.post", side_effect=requests.ConnectionError("down")):
        with pytest.raises(GenerationError):
            generator.generate("question", chunks)
