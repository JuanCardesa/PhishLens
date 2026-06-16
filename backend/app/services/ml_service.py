from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

from app.core.config import Settings, get_settings
from app.schemas.analysis import DOMFeatures
from app.services.feature_extractor import URLFeatures


FEATURE_ORDER = [
    "url_length",
    "num_dots",
    "num_hyphens",
    "uses_ip_domain",
    "has_at_symbol",
    "uses_https",
    "num_subdomains",
    "suspicious_keyword_count",
    "uses_punycode",
    "domain_entropy",
    "has_password_field",
    "num_forms",
    "external_form_action",
    "num_iframes",
    "external_links_ratio",
    "has_hidden_inputs",
]


@dataclass(frozen=True)
class MLResult:
    available: bool
    probability: float | None = None
    adjustment: int = 0
    error: str | None = None


def predict_ml_adjustment(
    url_features: URLFeatures,
    dom_features: DOMFeatures,
    settings: Settings | None = None,
) -> MLResult:
    settings = settings or get_settings()
    model_path = _resolve_model_path(settings.model_path)

    if not model_path.exists():
        return MLResult(available=False, error="model artifact not found")

    try:
        artifact = joblib.load(model_path)
        model = artifact["model"] if isinstance(artifact, dict) and "model" in artifact else artifact
        feature_order = artifact.get("feature_order", FEATURE_ORDER) if isinstance(artifact, dict) else FEATURE_ORDER
        values = _feature_values(url_features, dom_features)
        vector = [[values[name] for name in feature_order]]

        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(vector)[0]
            classes = list(getattr(model, "classes_", [0, 1]))
            positive_index = classes.index(1) if 1 in classes else len(probabilities) - 1
            probability = float(probabilities[positive_index])
        else:
            prediction = int(model.predict(vector)[0])
            probability = 0.85 if prediction == 1 else 0.15

        return MLResult(available=True, probability=probability, adjustment=_adjustment_from_probability(probability))
    except Exception as exc:  # pragma: no cover - defensive fallback around local artifacts.
        return MLResult(available=False, error=str(exc))


def is_model_available(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return _resolve_model_path(settings.model_path).exists()


def _resolve_model_path(configured_path: str) -> Path:
    path = Path(configured_path)
    if path.is_absolute():
        return path

    cwd_candidate = Path.cwd() / path
    if cwd_candidate.exists():
        return cwd_candidate

    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / path


def _feature_values(url_features: URLFeatures, dom_features: DOMFeatures) -> dict[str, Any]:
    return {
        "url_length": url_features.url_length,
        "num_dots": url_features.num_dots,
        "num_hyphens": url_features.num_hyphens,
        "uses_ip_domain": int(url_features.uses_ip_domain),
        "has_at_symbol": int(url_features.has_at_symbol),
        "uses_https": int(url_features.uses_https),
        "num_subdomains": url_features.num_subdomains,
        "suspicious_keyword_count": len(url_features.suspicious_keywords),
        "uses_punycode": int(url_features.uses_punycode),
        "domain_entropy": url_features.domain_entropy,
        "has_password_field": int(dom_features.has_password_field),
        "num_forms": dom_features.num_forms,
        "external_form_action": int(dom_features.external_form_action),
        "num_iframes": dom_features.num_iframes,
        "external_links_ratio": dom_features.external_links_ratio,
        "has_hidden_inputs": int(dom_features.has_hidden_inputs),
    }


def _adjustment_from_probability(probability: float) -> int:
    if probability >= 0.85:
        return 20
    if probability >= 0.65:
        return 12
    if probability <= 0.20:
        return -10
    if probability <= 0.35:
        return -5
    return 0
