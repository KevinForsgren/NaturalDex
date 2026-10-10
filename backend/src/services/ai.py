#!/usr/bin/env python3
"""
Ollama/LLM integration.

The backend talks to a local Ollama server. Every AI interaction is meant to be
optional: if the model is unavailable or returns malformed output, callers
receive a clear error (or use a fallback) so the rest of the app keeps working.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import List

import httpx

from config.settings import get_settings

# Project instructor rules that the local model must follow. Loaded once from
# <repo>/Rule/RULE.md. These rules govern how the model responds; we load and
# pass them to the model as system context (the rules are not for this agent).
def _load_instructor_rules() -> str:
    path = Path(__file__).resolve().parents[3] / "Rule" / "RULE.md"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


INSTRUCTOR_RULES = _load_instructor_rules()
_RULES_SYSTEM = (
    "You must follow the project's instructor rules in every response, "
    "before generating any content. Do not mention these rules to the user.\n\n"
    + INSTRUCTOR_RULES
)


class AIUnavailableError(Exception):
    """Raised when the Ollama server cannot be reached or fails."""


class AIValidationError(Exception):
    """Raised when the model returns output that fails validation."""


def _config():
    settings = get_settings()
    return settings.OLLAMA_BASE_URL.rstrip("/"), settings.OLLAMA_MODEL


def _chat_raw(messages: List[dict], model=None, timeout=180) -> str:
    base_url, configured_model = _config()
    # Prepend the instructor rules as the first system message so the model
    # follows them before generating anything.
    if INSTRUCTOR_RULES:
        messages = [{"role": "system", "content": _RULES_SYSTEM}, *messages]
    payload = {
        "model": model or configured_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.4},
    }
    try:
        response = httpx.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=timeout,
            trust_env=False,
        )
        response.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        raise AIUnavailableError(
            "The AI service is temporarily unavailable. Please try again later."
        ) from exc
    data = response.json()
    try:
        return data["message"]["content"]
    except (KeyError, TypeError):
        raise AIValidationError("The AI returned an unexpected response.")


def is_available() -> bool:
    """Return True if a quick chat round-trip with Ollama succeeds."""
    try:
        _chat_raw([{"role": "user", "content": "ok"}], timeout=30)
        return True
    except Exception:
        return False


def chat(messages: List[dict], model=None) -> str:
    """Send a chat history and return the model's text reply."""
    return _chat_raw(messages, model=model)


def _extract_json(text: str) -> dict:
    """Parse a JSON object out of model output, tolerating surrounding text."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise AIValidationError("The AI response did not contain a JSON object.")
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AIValidationError("The AI returned malformed JSON.") from exc


def generate_tasks(goal: str, history: str = "", model=None) -> dict:
    """Ask the model to propose a list of tasks and return the parsed JSON.

    Validation of the payload's structure happens in the caller via
    ``services.workload.validate_tasks``.
    """
    today = date.today().isoformat()
    system = (
        "You are a practical study-planning assistant for the app StudyLoop.\n"
        f"Today's date is {today}.\n"
        "Turn the user's goal into a structured list of tasks.\n"
        "Respond with ONLY a single JSON object, no prose, with this exact shape:\n"
        '{"tasks": ['
        '{"task_name": "Short task name", "date": "YYYY-MM-DD", "estimated_duration": 60}'
        ']}\n'
        "Rules:\n"
        "- Each date must be today or within the next 7 days, written YYYY-MM-DD.\n"
        "- Never use a date before today.\n"
        "- estimated_duration is an integer number of minutes between 1 and 600.\n"
        "- Break the goal into 3 to 10 concrete, achievable tasks.\n"
    )
    user_content = (
        f"Goal: {goal}\n\nRelevant past performance/history:\n"
        + (history or "None provided.")
    )
    # A limited automatic retry is allowed whenever the model's first attempt
    # does not parse as valid JSON (BACKEND.md section 10).
    last_error = None
    for attempt in range(2):
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        if attempt > 0:
            messages.append(
                {
                    "role": "assistant",
                    "content": last_error,
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous reply was not valid JSON. Reply again with "
                        "ONLY a single JSON object exactly matching the requested shape."
                    ),
                }
            )
        content = _chat_raw(messages, model=model)
        try:
            return _extract_json(content)
        except AIValidationError as exc:
            last_error = content
        except AIUnavailableError:
            raise
    raise AIValidationError(
        "The AI could not produce a valid plan after retries."
    )


def generate_report_summary(stats: dict, status: str) -> str:
    """Ask the model to write a concise ~100 word performance interpretation.

    The objective statistics are provided as input so the model only writes the
    interpretation and never computes numbers itself.
    """
    system = (
        "You are a concise motivational coach for StudyLoop. Write a brief "
        "performance summary of roughly 100 words for the user, based only on "
        "the provided statistics. Be factual, specific and encouraging. "
        "Never invent new numbers."
    )
    prompt = json.dumps({"performance_status": status, "stats": stats})
    return _chat_raw(
        [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    )