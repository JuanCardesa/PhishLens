from pathlib import Path

import joblib
import pytest

from app.core.config import Settings
from app.schemas.analysis import DOMFeatures
from app.services.feature_extractor import extract_url_features
from app.services.ml_service import (
    FEATURE_ORDER,
    _adjustment_from_probability,
    _artifact_cache_for_test,
    _load_artifact,
    _reset_artifact_cache,
    _resolve_model_path,
    is_model_available,
    predict_ml_adjustment,
    warm_up_model,
)


@pytest.fixture(autouse=True)
def reset_ml_cache():
    _reset_artifact_cache()
    yield
    _reset_artifact_cache()


class _ProbaModel:
    def __init__(self, probability: float) -> None:
        self.classes_ = [0, 1]
        self._probability = probability

    def predict_proba(self, vector):
        return [[1 - self._probability, self._probability]]


class _ProbaModelNoPositiveClass:
    """Simulates a model trained on a single class label only."""

    def __init__(self) -> None:
        self.classes_ = [0]

    def predict_proba(self, vector):
        return [[1.0]]


class _PredictOnlyModel:
    def __init__(self, prediction: int) -> None:
        self._prediction = prediction

    def predict(self, vector):
        return [self._prediction]


def _dump_model(tmp_path, model, name: str = "model.joblib"):
    path = tmp_path / name
    joblib.dump({"model": model, "feature_order": FEATURE_ORDER}, path)
    return path


def test_ml_service_falls_back_when_model_is_absent() -> None:
    result = predict_ml_adjustment(
        extract_url_features("https://example.com/login"),
        DOMFeatures(has_password_field=True, num_forms=1),
        settings=Settings(model_path="ml/models/does-not-exist.joblib"),
    )

    assert result.available is False
    assert result.adjustment == 0


def test_ml_model_availability_does_not_require_prediction() -> None:
    assert is_model_available(Settings(model_path="ml/models/does-not-exist.joblib")) is False


def test_predict_ml_adjustment_uses_predict_proba(tmp_path) -> None:
    model_path = _dump_model(tmp_path, _ProbaModel(0.9))

    result = predict_ml_adjustment(
        extract_url_features("https://example.com/login"),
        DOMFeatures(has_password_field=True, num_forms=1),
        settings=Settings(model_path=str(model_path)),
    )

    assert result.available is True
    assert result.probability == pytest.approx(0.9)
    assert result.adjustment == 20
    assert result.error is None


def test_warm_up_model_populates_cache_before_first_predict(tmp_path) -> None:
    model_path = _dump_model(tmp_path, _ProbaModel(0.9))
    settings = Settings(model_path=str(model_path))

    assert _artifact_cache_for_test() is None

    warm_up_model(settings)

    assert _artifact_cache_for_test() is not None


def test_warm_up_model_is_a_no_op_when_model_is_absent() -> None:
    warm_up_model(Settings(model_path="ml/models/does-not-exist.joblib"))

    assert _artifact_cache_for_test() is None


def test_load_artifact_caches_across_calls(tmp_path) -> None:
    model_path = _dump_model(tmp_path, _ProbaModel(0.9))

    first = _load_artifact(model_path)
    second = _load_artifact(model_path)

    assert second is first


def test_predict_ml_adjustment_falls_back_to_predict_when_no_predict_proba(tmp_path) -> None:
    model_path = _dump_model(tmp_path, _PredictOnlyModel(1))

    result = predict_ml_adjustment(
        extract_url_features("https://example.com/login"),
        DOMFeatures(),
        settings=Settings(model_path=str(model_path)),
    )

    assert result.available is True
    assert result.probability == pytest.approx(0.85)
    assert result.adjustment == 20


def test_predict_ml_adjustment_handles_missing_positive_class_label(tmp_path) -> None:
    model_path = _dump_model(tmp_path, _ProbaModelNoPositiveClass())

    result = predict_ml_adjustment(
        extract_url_features("https://example.com"),
        DOMFeatures(),
        settings=Settings(model_path=str(model_path)),
    )

    assert result.available is True
    assert result.probability == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("probability", "expected_adjustment"),
    [
        (0.9, 20),
        (0.7, 12),
        (0.5, 0),
        (0.3, -5),
        (0.1, -10),
    ],
)
def test_adjustment_from_probability_thresholds(probability: float, expected_adjustment: int) -> None:
    assert _adjustment_from_probability(probability) == expected_adjustment


def test_resolve_model_path_returns_absolute_path_unchanged(tmp_path) -> None:
    absolute = tmp_path / "model.joblib"
    assert _resolve_model_path(str(absolute)) == absolute


def test_resolve_model_path_relative_to_cwd(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    candidate = tmp_path / "model.joblib"
    candidate.write_bytes(b"stub")

    assert _resolve_model_path("model.joblib") == candidate


def test_resolve_model_path_relative_to_backend_root() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    expected = backend_root / "app" / "models" / "phishlens_model.joblib"

    assert _resolve_model_path("app/models/phishlens_model.joblib") == expected
