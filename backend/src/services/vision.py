#!/usr/bin/env python3
"""
Vision model provider layer (NatureDex).

The model runs only after all three discovery photos are submitted. It returns
advisory structured JSON which the backend validates and then applies its own
policy to decide acceptance. The model never persists anything, never awards XP,
and never decides authorization.

Providers: an OllamaVisionProvider talks to the user's local home base; a
deterministic MockVisionProvider exists for local dev and tests when Ollama is
not available. There is no cloud fallback.
"""

import base64
import json
import re
from pathlib import Path
from typing import List

import httpx

from config.settings import get_settings

# project vision-model rules, loaded dynamically relative to this file
# <repo root>/rule/RULE.md  (parents[3] == repo root)
RULE_PATH = Path(__file__).resolve().parents[3] / "rule" / "RULE.md"


def _load_rules() -> str:
    try:
        return RULE_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


INSTRUCTOR_RULES = _load_rules()

CATEGORIES = {"flora", "fauna", "fungi", "other", "uncertain"}
IMAGE_QUALITY = {"usable", "poor", "uncertain"}
GENUINENESS = {
    "no_obvious_manipulation_detected",
    "suspicious_screen_or_screenshot",
    "possible_duplicate_frames",
    "possible_manipulation",
    "inconclusive",
}
REASON_CODES = {
    None,
    "not_nature",
    "different_subjects",
    "image_quality_poor",
    "identification_uncertain",
    "suspicious_evidence",
    "unsupported_category",
}

# Backend policy threshold; the model's confidence is advisory, not a guarantee.
ACCEPTANCE_MIN_CONFIDENCE = 0.5
MAX_TEXT_LEN = 400


class VisionProviderError(Exception):
    """Base error for the vision provider."""


class VisionUnavailableError(VisionProviderError):
    """Raised when the model provider cannot be reached or lacks a vision model."""


class VisionValidationError(VisionProviderError):
    """Raised when the model output fails schema validation."""


class VisionRejectedError(VisionProviderError):
    """Raised when the model (or policy) rejects a discovery."""


def _str(value, field, max_len=MAX_TEXT_LEN):
    if value is None:
        return None
    if not isinstance(value, str):
        raise VisionValidationError(f"{field} must be a string.")
    value = value.strip()
    if len(value) > max_len:
        raise VisionValidationError(f"{field} is too long.")
    return value or None


def validate_model_output(raw) -> dict:
    """Validate the model's structured output; returns a normalized dict.

    Raises VisionValidationError for malformed output or out-of-range values.
    """
    if not isinstance(raw, dict):
        raise VisionValidationError("Model output must be a JSON object.")

    accepted = raw.get("accepted")
    if not isinstance(accepted, bool):
        raise VisionValidationError("accepted must be a boolean.")

    category = raw.get("category")
    if category not in CATEGORIES:
        raise VisionValidationError(f"category is invalid: {category!r}")

    confidence = raw.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise VisionValidationError("confidence must be a number.")
    confidence = float(confidence)
    if not (0.0 <= confidence <= 1.0):
        raise VisionValidationError("confidence must be within [0, 1].")

    same_subject = raw.get("sameSubjectAcrossImages")
    if not isinstance(same_subject, bool):
        raise VisionValidationError("sameSubjectAcrossImages must be a boolean.")

    image_quality = raw.get("imageQuality")
    if image_quality not in IMAGE_QUALITY:
        raise VisionValidationError(f"imageQuality is invalid: {image_quality!r}")

    genuineness = raw.get("genuinenessAssessment")
    if genuineness not in GENUINENESS:
        raise VisionValidationError(f"genuinenessAssessment is invalid: {genuineness!r}")

    reason = raw.get("reasonCode")
    if reason not in REASON_CODES:
        raise VisionValidationError(f"reasonCode is invalid: {reason!r}")

    return {
        "accepted": accepted,
        "category": category,
        "commonName": _str(raw.get("commonName"), "commonName"),
        "scientificName": _str(raw.get("scientificName"), "scientificName"),
        "confidence": confidence,
        "sameSubjectAcrossImages": same_subject,
        "imageQuality": image_quality,
        "genuinenessAssessment": genuineness,
        "reasonCode": reason,
        "summary": _str(raw.get("summary"), "summary"),
        "interestingFact": _str(raw.get("interestingFact"), "interestingFact"),
    }


def classify_rejection(result: dict) -> tuple:
    """Apply backend policy to an advisory model result.

    Returns ``(accepted, category_or_None, error_code, genuineness_status)``.
    ``accepted`` is True only when the discovery should create/increment a card.
    """
    if not result["accepted"]:
        return (False, None, result["reasonCode"], "flagged" if result["genuinenessAssessment"].startswith("suspicious") or result["genuinenessAssessment"] == "inconclusive" else "inconclusive")
    if result["category"] in ("other", "uncertain"):
        return (False, None, "unsupported_category", "inconclusive")
    if not result["sameSubjectAcrossImages"]:
        return (False, None, "different_subjects", "inconclusive")
    if result["imageQuality"] != "usable":
        return (False, None, "image_quality_poor", "inconclusive")
    if result["confidence"] < ACCEPTANCE_MIN_CONFIDENCE:
        return (False, None, "identification_uncertain", "inconclusive")
    if result["genuinenessAssessment"] != "no_obvious_manipulation_detected":
        return (False, None, "suspicious_evidence", "flagged")
    return (True, result["category"], None, "passed_checks")


# --------------------------------------------------------------------------
# Providers
# --------------------------------------------------------------------------
class VisionProvider:
    name = "base"

    def analyze(self, images: List[bytes], context: dict) -> dict:
        raise NotImplementedError

    def is_available(self) -> bool:
        return True


class MockVisionProvider(VisionProvider):
    """Deterministic provider for local dev and tests (no model, no network)."""

    name = "mock"

    def is_available(self) -> bool:
        return True

    def analyze(self, images: List[bytes], context: dict) -> dict:
        category = (context or {}).get("category_hint") or "flora"
        if category not in {"flora", "fauna", "fungi"}:
            category = "flora"
        return {
            "accepted": True,
            "category": category,
            "commonName": "Bougainvillea",
            "scientificName": None,
            "confidence": 0.91,
            "sameSubjectAcrossImages": True,
            "imageQuality": "usable",
            "genuinenessAssessment": "no_obvious_manipulation_detected",
            "reasonCode": None,
            "summary": "A flowering ornamental shrub with vivid papery bracts.",
            "interestingFact": "The colorful structures are bracts surrounding small flowers.",
        }


class OllamaVisionProvider(VisionProvider):
    """Talks to the user's local Ollama home base with a vision-capable model."""

    name = "ollama"

    def _base_url(self) -> str:
        return get_settings().OLLAMA_BASE_URL.rstrip("/")

    def _model(self) -> str:
        return get_settings().OLLAMA_MODEL

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self._base_url()}/api/tags", timeout=10, trust_env=False)
            r.raise_for_status()
            return True
        except Exception:
            return False

    def analyze(self, images: List[bytes], context: dict) -> dict:
        settings = get_settings()
        system = (
            "You are the NatureDex submitted-image checker and nature "
            "identification model. Follow the supplied rules exactly and return "
            "ONLY a single JSON object with no markdown fences and no extra text."
        )
        prompt = (
            "Identify the organism in the three photos (they show one subject "
            "from three angles). Respond with a single JSON object following the "
            "required schema. Category hint from the user: "
            f"{context.get('category_hint') or 'none'}. Refer to the rules for the "
            "exact fields and allowed values."
        )
        payload = {
            "model": self._model(),
            "prompt": prompt,
            "images": [base64.b64encode(b).decode("ascii") for b in images],
            "system": f"{system}\n\n{INSTRUCTOR_RULES}" if INSTRUCTOR_RULES else system,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        try:
            response = httpx.post(
                f"{self._base_url()}/api/generate",
                json=payload,
                timeout=180,
                trust_env=False,
            )
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            raise VisionUnavailableError(
                "AI home base unavailable. Please try again."
            ) from exc

        try:
            content = response.json().get("response", "")
        except (ValueError, KeyError):
            raise VisionValidationError("The vision model returned an unexpected response.")

        raw = _extract_json(content)
        return validate_model_output(raw)


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise VisionValidationError("The vision model did not return a JSON object.")
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise VisionValidationError("The vision model returned malformed JSON.") from exc


def get_vision_provider() -> VisionProvider:
    provider = get_settings().VISION_PROVIDER
    if provider == "mock":
        return MockVisionProvider()
    if provider == "ollama":
        return OllamaVisionProvider()
    raise VisionUnavailableError(f"Unknown VISION_PROVIDER: {provider!r}")