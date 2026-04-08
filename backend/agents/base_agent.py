"""
agents/base_agent.py — Abstract base class for all MolForge AI agents.

All 8 agents inherit from BaseAgent. It provides:
  - Abstract run() interface
  - emit() helper for status_updates + WebSocket streaming
  - fetch_with_retry() for resilient HTTP calls (3 attempts, exponential backoff)
  - parse_gemini_json() for safely parsing Gemini responses that may be markdown-wrapped

HIGH RISK — all 8 agents inherit from this. Run gitnexus_impact before editing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from orchestrator.state import MolForgeState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base for all MolForge AI pipeline agents."""

    name: str = "base_agent"

    @abstractmethod
    async def run(self, state: MolForgeState) -> MolForgeState:
        """
        Execute this agent's logic. Must:
          1. Call self.emit(state, "AgentName: starting...") at the top
          2. Write results only to this agent's designated state fields
          3. Collect non-fatal errors via state["errors"].append(...)
          4. Call self.emit(state, "AgentName: done — <summary>") at the end
          5. Always return the modified state
        """
        ...

    # ------------------------------------------------------------------
    # Status streaming helper
    # ------------------------------------------------------------------

    def emit(self, state: MolForgeState, message: str) -> None:
        """
        Append a status message to state["status_updates"].

        The WebSocket manager watches status_updates and streams new entries
        to the frontend in real time. Always call this at agent start and end,
        and at meaningful milestones within the agent.
        """
        state["status_updates"].append(message)
        logger.info("[%s] %s", self.name, message)

    # ------------------------------------------------------------------
    # HTTP helper with retry
    # ------------------------------------------------------------------

    async def fetch_with_retry(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        method: str = "GET",
        json_body: dict[str, Any] | None = None,
        max_retries: int = 3,
        timeout: float = 30.0,
    ) -> dict[str, Any] | list | None:
        """
        Make an HTTP request with exponential backoff retry.

        Retries on: 429 (rate limit), 500, 502, 503, 504, and network errors.
        Returns parsed JSON on success, None on exhausted retries.

        All external API calls in agents must use this method — never call
        httpx directly without retry logic.
        """
        last_exc: Exception | None = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if method.upper() == "GET":
                        resp = await client.get(url, params=params, headers=headers)
                    elif method.upper() == "POST":
                        resp = await client.post(url, params=params, headers=headers, json=json_body)
                    else:
                        resp = await client.request(method, url, params=params, headers=headers, json=json_body)

                    logger.debug("[%s] %s %s → %d", self.name, method, url, resp.status_code)

                    if resp.status_code in (429, 500, 502, 503, 504):
                        wait = 2 ** attempt
                        logger.warning(
                            "[%s] HTTP %d on attempt %d/%d, retrying in %ds",
                            self.name, resp.status_code, attempt + 1, max_retries, wait,
                        )
                        await asyncio.sleep(wait)
                        continue

                    resp.raise_for_status()
                    return resp.json()

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning(
                    "[%s] Network error on attempt %d/%d: %s, retrying in %ds",
                    self.name, attempt + 1, max_retries, exc, wait,
                )
                await asyncio.sleep(wait)

        logger.error("[%s] All %d retries exhausted for %s. Last error: %s", self.name, max_retries, url, last_exc)
        return None

    # ------------------------------------------------------------------
    # Gemini response parser
    # ------------------------------------------------------------------

    @staticmethod
    def parse_gemini_json(text: str) -> Any:
        """
        Safely parse JSON from a Gemini response.

        Gemini often wraps JSON in markdown code fences (```json ... ```).
        This method strips fences, trims whitespace, and parses the result.

        Returns the parsed Python object, or None if parsing fails.
        Always null-check the return value before using it.

        Example:
            raw = '```json\\n[{"gene": "LRRK2"}]\\n```'
            data = BaseAgent.parse_gemini_json(raw)
            # → [{"gene": "LRRK2"}]
        """
        if not text:
            return None

        # Strip markdown code fences: ```json ... ``` or ``` ... ```
        cleaned = re.sub(r"```(?:json)?\s*", "", text)
        cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("parse_gemini_json failed: %s\nRaw text (first 500 chars): %.500s", exc, text)
            return None
