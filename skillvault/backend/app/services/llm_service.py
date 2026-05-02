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

    def summarize_document(self, text: str, file_path: str | None = None, repo: str | None = None) -> dict:
        if not self.api_key:
            snippet = text[:500]
            return {
                "title": file_path or "Mock Summary",
                "summary": snippet or "暂无摘要内容",
                "key_points": ["mock-mode", "未配置 LLM_API_KEY，返回摘录"],
                "tags": ["mock", "summary", "excerpt"],
                "category": "general",
                "quality_score": 50,
                "visibility": "private",
                "recommend_level": "中",
            }

        prompt = """
请用中文总结下面这份 GitHub 项目文档，输出 JSON，字段必须包含：
title, summary, key_points(数组), tags(数组), category, quality_score(0-100), visibility, recommend_level

要求：
1) summary 不超过 200 字
2) 说明文档主要讲什么、适合谁看、可沉淀什么知识资产
3) recommend_level 只能是：高/中/低
4) 不要编造文档没有的信息
"""
        content = self.chat([
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"repo={repo}\nfile_path={file_path}\n\n{text[:12000]}"},
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
                "recommend_level": "中",
            }

    def generate_repo_overview(self, *, repo_name: str, docs_context: str, sync_stats: dict) -> str:
        if not self.api_key:
            return (
                f"# 项目简介\n{repo_name} 的自动概览（Mock 模式）。\n\n"
                "# 同步概览\n"
                f"- 本次新增文档：{sync_stats.get('created_docs', 0)}\n"
                f"- 本次更新文档：{sync_stats.get('updated_docs', 0)}\n"
                f"- 本次跳过未变化：{sync_stats.get('unchanged_docs', 0)}\n\n"
                "# 说明\n未配置 LLM_API_KEY，建议查看 README 获取更多信息。"
            )

        prompt = """
请根据给定的 GitHub 仓库文档片段，用中文生成项目概览（Markdown）：
1. 一句话说明项目是干什么的
2. 主要能力（列表）
3. 适合沉淀的知识资产（列表）
4. 推荐先看的文档（列表）
5. 可能可生成的 Skill 方向（列表）

限制：
- 不超过 800 字
- 不编造不存在的信息
- 如果信息不足，明确写“信息不足”
"""
        user_content = (
            f"repo={repo_name}\n"
            f"sync_stats={sync_stats}\n\n"
            f"docs_context:\n{docs_context[:15000]}"
        )
        return self.chat(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
        )

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
