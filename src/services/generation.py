import os
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
# -1 tells Ollama to generate until a natural stop or the model's context
# limit, instead of the model's own (often short) default cutoff.
OLLAMA_NUM_PREDICT = int(os.environ.get("OLLAMA_NUM_PREDICT", "-1"))
# Lower than Ollama's 0.8 default: favors direct, consistent answers over
# creative variation, which matters more for grounded Q&A than for prose.
OLLAMA_TEMPERATURE = float(os.environ.get("OLLAMA_TEMPERATURE", "0.3"))

class GenerationError(Exception):
    pass

class AnswerGenerator:
    def __init__(
        self,
        url: str = OLLAMA_URL,
        model: str = OLLAMA_MODEL,
        num_predict: int = OLLAMA_NUM_PREDICT,
        temperature: float = OLLAMA_TEMPERATURE,
    ):
        self.url = url
        self.model = model
        self.num_predict = num_predict
        self.temperature = temperature

    def _build_prompt(self, query: str, chunks: list) -> str:
        context = "\n\n".join(
            f"[{i + 1}] {c['text']}" for i, c in enumerate(chunks)
        )
        return (
            "You are a precise research assistant. Answer the question "
            "directly and concisely using only the context below. If "
            "different sources each cover part of the answer, synthesize "
            "them into one coherent answer rather than listing sources "
            "separately. Cite sources inline with their bracketed number, "
            "e.g. [1], [2].\n\n"
            "Do not add commentary about what the context does or doesn't "
            "explicitly say, or how complete it is — just answer with what's "
            "there. Only state that the context doesn't address the "
            "question if none of it is actually relevant, and if so say "
            "that in one short sentence, nothing more. Do not use knowledge "
            "from outside this context.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}\n\nAnswer:"
        )

    def generate(self, query: str, chunks: list, num_predict: int = None) -> str:
        if not chunks:
            return "No relevant context was found to answer this question."

        prompt = self._build_prompt(query, chunks)
        effective_num_predict = num_predict if num_predict is not None else self.num_predict
        try:
            resp = requests.post(
                f"{self.url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": effective_num_predict,
                        "temperature": self.temperature
                    }
                },
                timeout=120
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise GenerationError(f"LLM generation failed: {e}")

        return resp.json().get("response", "").strip()
