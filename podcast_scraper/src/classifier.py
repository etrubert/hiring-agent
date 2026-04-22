"""Classify podcast guests by role using either Anthropic Claude or Ollama."""

import json
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from config import ROLES

logger = logging.getLogger(__name__)


class GuestClassification(BaseModel):
    is_ai_guest: bool = Field(description="Whether the interviewed guest works on AI/ML")
    role_detected: str = Field(description="One of the predefined roles or 'Other'")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in 0-1 range")
    guest_name: Optional[str] = Field(default=None, description="Best guess for the guest name, or null")
    reasoning: str = Field(description="One-sentence justification")


SYSTEM_PROMPT = f"""You are an expert recruiter assistant. Given a podcast episode title + description,
decide whether the interviewed guest is an AI/ML professional, pick the most accurate role, and extract
the guest name. Be conservative — if the episode is NOT an interview with an AI practitioner, set
is_ai_guest=false and role_detected='Other'.

Allowed roles: {ROLES}

Definitions:
- AI Engineer / ML Engineer: builds production AI/ML systems
- AI Researcher: publishes research, works in labs
- Agent Builder: builds autonomous agents, tool use, orchestration
- LLM Engineer: specialized on LLM apps (RAG, fine-tuning, prompt eng)
- AI Founder: founder/CEO of an AI company
- AI Product Manager: PM for AI products
- AI Engineering Manager: manages AI/ML teams
- Data Scientist: analytics / modelling / stats focus
- Other: anything else, including non-AI guests or hosts solo

Return ONLY a JSON object with keys: is_ai_guest (bool), role_detected (string), confidence (0-1 float),
guest_name (string or null), reasoning (string). No markdown, no preamble."""


def _parse_json_response(raw: str) -> Optional[Dict]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None


class Classifier:
    def __init__(
        self,
        provider: str = "anthropic",
        anthropic_api_key: str = "",
        claude_model: str = "claude-haiku-4-5",
        ollama_model: str = "gemma3:4b",
    ):
        self.provider = provider.lower()
        if self.provider == "anthropic":
            if not anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required for anthropic provider")
            from anthropic import Anthropic
            self.client = Anthropic(api_key=anthropic_api_key)
            self.model = claude_model
        elif self.provider == "ollama":
            import ollama
            self.client = ollama
            self.model = ollama_model
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {provider}")

    def _user_content(self, title: str, description: str, channel: str) -> str:
        return (
            f"Channel: {channel}\n"
            f"Title: {title}\n"
            f"Description: {description[:2000]}"
        )

    def _classify_anthropic(self, content: str) -> str:
        from anthropic import APIError  # local import to keep ollama-only envs lean
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": content}],
        )
        return "".join(
            block.text for block in msg.content if getattr(block, "type", None) == "text"
        ).strip()

    def _classify_ollama(self, content: str) -> str:
        resp = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            format="json",
            options={"temperature": 0.1, "top_p": 0.9, "num_ctx": 8192},
        )
        return resp.get("message", {}).get("content", "").strip()

    def classify(self, title: str, description: str, channel: str = "") -> Optional[GuestClassification]:
        content = self._user_content(title, description, channel)
        try:
            raw = (
                self._classify_anthropic(content)
                if self.provider == "anthropic"
                else self._classify_ollama(content)
            )
        except Exception as exc:
            logger.warning("classifier LLM call failed: %s", exc)
            raise

        data = _parse_json_response(raw)
        if data is None:
            logger.warning("classifier: could not parse JSON — raw=%r", raw[:200])
            return None
        if data.get("role_detected") not in ROLES:
            data["role_detected"] = "Other"
        try:
            return GuestClassification(**data)
        except Exception as exc:
            logger.warning("classifier: pydantic validation failed: %s — data=%r", exc, data)
            return None
