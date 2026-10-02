"""
core/laya_router.py — Secondary Intent Router & Confidence Estimator.

Provides an isolated classification interface (Layer 2) between deterministic Fast Intent
and Groq LLM fallback.
Lead Architect: Hamza Bukhari
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class LayaClassification:
    intent: str
    target: Optional[str] = None
    confidence: float = 0.0
    action: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class LayaRouter:
    """Isolated secondary classifier with confidence gating and abstention."""

    def __init__(self, confidence_threshold: float = 0.75):
        self.confidence_threshold = confidence_threshold
        self._enabled = True

    def classify(self, text: str, log: Optional[Callable[[str], None]] = None) -> Optional[LayaClassification]:
        """Classify utterance intent when deterministic match does not trigger.

        Returns LayaClassification if confident, otherwise None (abstains to LLM).
        """
        if not text or not self._enabled:
            return None

        t0 = time.time()
        if log:
            log(f"[TIMING] LAYA start: {t0:.3f}")

        classification: Optional[LayaClassification] = None

        try:
            # Check for high-intent semantic patterns that might have slight variations
            raw = text.strip().lower()

            # Example: conversational app openings: "i want to code in vscode" / "switch to chrome"
            if any(k in raw for k in ("switch to", "bring up", "show me")) and any(app in raw for k, app in [("chrome", "chrome"), ("code", "vscode"), ("calculator", "calculator")]):
                for app in ("chrome", "calculator", "vscode", "spotify", "discord", "notepad"):
                    if app in raw:
                        classification = LayaClassification(
                            intent="open_app",
                            target=app,
                            confidence=0.85,
                            action="open",
                            parameters={"app_name": app, "action": "open"},
                        )
                        break

            # If classification score below threshold, abstain to LLM
            if classification and classification.confidence < self.confidence_threshold:
                classification = None

        except Exception as e:
            if log:
                log(f"[LAYA] error during classification: {e}")
            classification = None
        finally:
            t1 = time.time()
            if log:
                log(f"[TIMING] LAYA end: {t1:.3f}")
                elapsed_ms = (t1 - t0) * 1000.0
                log(f"[TIMING] LAYA total={elapsed_ms:.1f}ms")

        return classification


# Singleton router instance
_laya_router = LayaRouter()


def classify_with_laya(text: str, log: Optional[Callable[[str], None]] = None) -> Optional[LayaClassification]:
    """Public helper for secondary intent classification."""
    return _laya_router.classify(text, log=log)
