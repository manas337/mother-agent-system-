"""
LLM Provider Abstraction Layer - Supports multiple LLM backends
"""

import os
import json
import re
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import httpx


def _repair_truncated_json(text: str) -> str:
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in '{[':
            stack.append(ch)
        elif ch == '}':
            if stack and stack[-1] == '{':
                stack.pop()
            else:
                return ""
        elif ch == ']':
            if stack and stack[-1] == '[':
                stack.pop()
            else:
                return ""
    closing = { '{': '}', '[': ']' }
    for opener in reversed(stack):
        text += closing[opener]
    return text


def extract_json(text: str) -> Dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    repaired = _repair_truncated_json(text)
    if repaired:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{[\s\S]*\}", candidate)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    raise json.JSONDecodeError(f"Could not extract JSON from: {text[:200]}", text, 0)


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        pass

    @abstractmethod
    def generate_json(self, prompt: str, max_tokens: int = 1000) -> Dict:
        pass


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def generate_json(self, prompt: str, max_tokens: int = 1000) -> Dict:
        response = self.generate(prompt, max_tokens)
        return extract_json(response)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def generate_json(self, prompt: str, max_tokens: int = 1000) -> Dict:
        response = self.generate(prompt, max_tokens)
        return extract_json(response)


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model_name = model

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={"max_output_tokens": max_tokens}
        )
        return response.text

    def generate_json(self, prompt: str, max_tokens: int = 1000) -> Dict:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt + "\n\nReturn ONLY valid JSON. No markdown, no explanation.",
            config={
                "max_output_tokens": max_tokens,
                "response_mime_type": "application/json"
            }
        )
        return extract_json(response.text)


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.client = httpx.Client(base_url=self.base_url, headers=headers, timeout=60.0)

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        for attempt in range(3):
            try:
                response = self.client.post("/api/generate", json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "num_ctx": 16384
                    }
                })
                response.raise_for_status()
                data = response.json()
                if "response" in data:
                    return data["response"]
                raise ValueError(f"Unexpected Ollama response: {data}")
            except httpx.ReadTimeout:
                if attempt < 2:
                    time.sleep(2)
                else:
                    raise

    def generate_json(self, prompt: str, max_tokens: int = 1000) -> Dict:
        response = self.generate(prompt, max_tokens)
        return extract_json(response)


class MockProvider(LLMProvider):
    """Mock provider for offline testing - no API key needed"""

    def __init__(self, model: str = "mock"):
        self.model = model
        self.call_count = 0

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        self.call_count += 1
        return json.dumps(self._mock_response(prompt))

    def generate_json(self, prompt: str, max_tokens: int = 1000) -> Dict:
        self.call_count += 1
        return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> Dict:
        if "is_complete" in prompt:
            return {
                "is_complete": True,
                "missing_elements": [],
                "clarifying_questions": [],
                "interpreted_spec": {
                    "project_type": "web_app",
                    "core_features": ["feature1", "feature2"],
                    "tech_stack": {"frontend": "react", "backend": "python"},
                    "complexity": "simple"
                }
            }
        if "task_id" in prompt:
            return [
                {
                    "task_id": "task_1",
                    "description": "Backend API",
                    "role": "BACKEND",
                    "dependencies": [],
                    "deliverables": ["API endpoints"]
                },
                {
                    "task_id": "task_2",
                    "description": "Frontend UI",
                    "role": "FRONTEND",
                    "dependencies": [],
                    "deliverables": ["React components"]
                }
            ]
        if "is_valid" in prompt:
            return {
                "is_valid": True,
                "issues": [],
                "quality_score": 1.0,
                "recommendations": []
            }
        if "consolidating" in prompt or "Consolidating" in prompt:
            return {
                "files": {
                    "backend/app.py": "print('hello')",
                    "frontend/App.jsx": "export default function App() {}"
                },
                "readme": "# Test Project\n\nGenerated by Mother-Agent",
                "summary": "Successfully built the project"
            }
        return {"status": "completed", "summary": "Mock execution"}


def create_provider(config: Dict) -> LLMProvider:
    provider_type = config.get("provider", "ollama").lower().strip()
    if provider_type == "mock":
        return MockProvider(model=config.get("model", "mock"))
    if provider_type == "ollama":
        return OllamaProvider(
            base_url=config.get("base_url", "http://localhost:11434"),
            model=config.get("model", "llama3"),
            api_key=config.get("api_key", "")
        )
    elif provider_type == "gemini":
        return GeminiProvider(
            api_key=config["api_key"],
            model=config.get("model", "gemini-2.0-flash")
        )
    elif provider_type == "anthropic":
        return AnthropicProvider(
            api_key=config["api_key"],
            model=config.get("model", "claude-sonnet-4-20250514")
        )
    elif provider_type == "openai":
        return OpenAIProvider(
            api_key=config["api_key"],
            model=config.get("model", "gpt-4o")
        )
    else:
        raise ValueError(f"Unknown provider: {provider_type}")


def load_llm_config() -> Dict:
    provider = (os.environ.get("LLM_PROVIDER") or "ollama").lower().strip()
    config = {"provider": provider}
    if provider == "ollama":
        config["base_url"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        config["api_key"] = os.getenv("OLLAMA_API_KEY", "")
        config["model"] = os.getenv("LLM_MODEL", "llama3")
    elif provider == "gemini":
        config["api_key"] = os.getenv("GEMINI_API_KEY", "")
        config["model"] = os.getenv("LLM_MODEL", "gemini-2.0-flash")
    elif provider == "anthropic":
        config["api_key"] = os.getenv("ANTHROPIC_API_KEY", "")
        config["model"] = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
    elif provider == "openai":
        config["api_key"] = os.getenv("OPENAI_API_KEY", "")
        config["model"] = os.getenv("LLM_MODEL", "gpt-4o")
    return config
