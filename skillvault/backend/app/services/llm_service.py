from __future__ import annotations

import json
import httpx

from app.core.config import settings


class LLMServiceError(RuntimeError):
    pass


class LLMService:
    def __init__(self) -> None:
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model

    def chat(self, messages: list[dict], temperature: float = 0.2) -> str:
        if not self.api_key:
            return "[MOCK] LLM response generated without API key."

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        try:
            res = httpx.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=90)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise LLMServiceError(f"LLM API failed: {exc}") from exc

    def summarize_document(self, text: str) -> dict:
        if not self.api_key:
            snippet = text[:500]
            return {
                "title": "Mock Summary",
                "summary": snippet,
                "key_points": ["mock-mode", "add LLM_API_KEY for real summary"],
                "tags": ["mock", "summary"],
                "category": "general",
                "quality_score": 50,
                "visibility": "private",
            }

        prompt = (
            "Summarize the document as JSON with keys: title, summary, key_points(list), "
            "tags(list), category, quality_score(0-100), visibility."
        )
        content = self.chat([
            {"role": "system", "content": prompt},
            {"role": "user", "content": text[:12000]},
        ])
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "title": "Summary",
                "summary": content,
                "key_points": [],
                "tags": [],
                "category": "general",
                "quality_score": 60,
                "visibility": "private",
            }

    def generate_skill_candidate(self, text: str, source_metadata: dict) -> dict:
        if not self.api_key:
            return {
                "title": source_metadata.get("title", "Mock Skill Candidate"),
                "scenario": "Extract reusable workflow from source document",
                "input_schema": {"type": "object", "properties": {"input": {"type": "string"}}},
                "prompt_template": "You are an assistant. Use context: {{context}}. User input: {{input}}",
                "output_format": "markdown",
                "examples": [{"input": "example", "output": "example output"}],
                "tags": ["mock", "skill"],
            }

        prompt = (
            "Generate a skill candidate as JSON with keys: title, scenario, input_schema, "
            "prompt_template, output_format, examples(list), tags(list)."
        )
        content = self.chat([
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"source_meta={source_metadata}\n\ntext={text[:12000]}"},
        ])
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "title": source_metadata.get("title", "Generated Skill"),
                "scenario": "General",
                "input_schema": {},
                "prompt_template": content,
                "output_format": "text",
                "examples": [],
                "tags": [],
            }
