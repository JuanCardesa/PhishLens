from app.core.config import Settings
from app.schemas.analysis import DOMFeatures
from app.services.feature_extractor import extract_url_features
from app.services.ml_service import predict_ml_adjustment


def test_ml_service_falls_back_when_model_is_absent() -> None:
    result = predict_ml_adjustment(
        extract_url_features("https://example.com/login"),
        DOMFeatures(has_password_field=True, num_forms=1),
        settings=Settings(model_path="ml/models/does-not-exist.joblib"),
    )

    assert result.available is False
    assert result.adjustment == 0
