from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import joblib
import numpy as np
import shap

from app.core.config import Settings, get_settings
from app.schemas.analysis import DOMFeatures
from app.services.feature_extractor import URLFeatures

logger = logging.getLogger(__name__)


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

# Short, human-readable labels for the top-contributing-factors explanation.
FEATURE_LABELS = {
    "url_length": "URL length",
    "num_dots": "number of dots in the URL",
    "num_hyphens": "number of hyphens in the URL",
    "uses_ip_domain": "IP address used as the domain",
    "has_at_symbol": "@ symbol in the URL",
    "uses_https": "HTTPS usage",
    "num_subdomains": "number of subdomains",
    "suspicious_keyword_count": "suspicious keyword count",
    "uses_punycode": "punycode usage",
    "domain_entropy": "domain character entropy",
    "has_password_field": "presence of a password field",
    "num_forms": "number of forms",
    "external_form_action": "form submitting to an external domain",
    "num_iframes": "number of iframes",
    "external_links_ratio": "ratio of external links",
    "has_hidden_inputs": "presence of hidden form inputs",
}

_TOP_FACTOR_COUNT = 2


@dataclass(frozen=True)
class MLResult:
    available: bool
    probability: float | None = None
    adjustment: int = 0
    error: str | None = None
    top_factors: tuple[str, ...] = ()


@dataclass
class _ModelArtifact:
    model: Any
    feature_order: list[str]
    sha256_prefix: str
    explainer: Any | None = None


_artifact_cache: _ModelArtifact | None = None
_artifact_lock = Lock()


def _load_artifact(model_path: Path) -> _ModelArtifact:
    """Load and cache the model artifact on first call; return cached on subsequent calls."""
    global _artifact_cache
    if _artifact_cache is not None:
        return _artifact_cache

    with _artifact_lock:
        # Double-checked locking: another thread may have loaded while we waited.
        if _artifact_cache is not None:
            return _artifact_cache

        file_bytes = model_path.read_bytes()
        sha256_prefix = hashlib.sha256(file_bytes).hexdigest()[:16]
        logger.info("ml_model_loaded path=%s sha256_prefix=%s", model_path, sha256_prefix)

        raw = joblib.load(model_path)
        model = raw["model"] if isinstance(raw, dict) and "model" in raw else raw
        feature_order = raw.get("feature_order", FEATURE_ORDER) if isinstance(raw, dict) else FEATURE_ORDER

        explainer = None
        try:
            explainer = shap.TreeExplainer(model)
        except Exception:  # noqa: BLE001 - not every model type supports TreeExplainer
            logger.info("shap_explainer_unavailable model_type=%s", type(model).__name__)

        _artifact_cache = _ModelArtifact(
            model=model, feature_order=feature_order, sha256_prefix=sha256_prefix, explainer=explainer
        )

    return _artifact_cache


def _reset_artifact_cache() -> None:
    """Clear the in-memory model cache. Intended for tests only."""
    global _artifact_cache
    with _artifact_lock:
        _artifact_cache = None


def _artifact_cache_for_test() -> _ModelArtifact | None:
    """Read the in-memory model cache. Intended for tests only."""
    return _artifact_cache


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
        artifact = _load_artifact(model_path)
        values = _feature_values(url_features, dom_features)
        vector = [[values[name] for name in artifact.feature_order]]

        if hasattr(artifact.model, "predict_proba"):
            probabilities = artifact.model.predict_proba(vector)[0]
            classes = list(getattr(artifact.model, "classes_", [0, 1]))
            positive_index = classes.index(1) if 1 in classes else len(probabilities) - 1
            probability = float(probabilities[positive_index])
        else:
            prediction = int(artifact.model.predict(vector)[0])
            probability = 0.85 if prediction == 1 else 0.15

        top_factors = _top_factors_for_prediction(artifact, vector)

        return MLResult(
            available=True,
            probability=probability,
            adjustment=_adjustment_from_probability(probability),
            top_factors=top_factors,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback around local artifacts.
        return MLResult(available=False, error=str(exc))


def _top_factors_for_prediction(artifact: _ModelArtifact, vector: list[list[Any]]) -> tuple[str, ...]:
    """Return the top contributing feature labels for this single prediction.

    Uses SHAP TreeExplainer values for this specific input, not the model's global
    feature_importances_ — the explanation is for this URL/page, not the model overall.
    Best-effort: any failure (unsupported model, shape mismatch) falls back to no
    explanation rather than breaking the prediction that already succeeded above.
    """
    if artifact.explainer is None:
        return ()

    try:
        shap_values = np.array(artifact.explainer.shap_values(np.array(vector, dtype=float)))
        # Binary classifiers: shape (1, n_features, 2) -> take the positive class.
        contributions = shap_values[0, :, -1] if shap_values.ndim == 3 else shap_values[0]
        ranked = sorted(
            zip(artifact.feature_order, contributions), key=lambda pair: abs(pair[1]), reverse=True
        )
        return tuple(
            FEATURE_LABELS.get(name, name) for name, value in ranked[:_TOP_FACTOR_COUNT] if abs(value) > 0
        )
    except Exception:  # noqa: BLE001 - explanation is best-effort, never blocks scoring
        return ()


def warm_up_model(settings: Settings | None = None) -> None:
    """Eagerly load the model artifact so the first real request isn't slow.

    Unpickling a scikit-learn estimator triggers a lazy import of sklearn's
    compiled submodules (and transitively numpy/scipy), which can take seconds
    on a cold process. Without this, that cost lands on whichever user request
    happens to be first — and predict_ml_adjustment runs synchronously, so it
    blocks the event loop for other concurrent requests too. Called once from
    the app startup lifespan; failures are swallowed because a missing/corrupt
    model artifact is an expected, already-handled fallback path, not a reason
    to fail startup.
    """
    settings = settings or get_settings()
    model_path = _resolve_model_path(settings.model_path)
    if not model_path.exists():
        return

    try:
        _load_artifact(model_path)
    except Exception:  # noqa: BLE001 - best-effort warm-up, real errors surface on first predict
        logger.warning("ml_model_warm_up_failed path=%s", model_path, exc_info=True)


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

    backend_root = Path(__file__).resolve().parents[2]
    backend_candidate = backend_root / path
    if backend_candidate.exists():
        return backend_candidate

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
