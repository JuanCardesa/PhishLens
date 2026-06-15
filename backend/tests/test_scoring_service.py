import pytest

from app.schemas.analysis import AnalysisRequest, DOMFeatures
from app.services.scoring_service import analyze_url, label_from_score


def test_label_from_score_thresholds() -> None:
    assert label_from_score(0) == "safe"
    assert label_from_score(34) == "safe"
    assert label_from_score(35) == "suspicious"
    assert label_from_score(69) == "suspicious"
    assert label_from_score(70) == "dangerous"


@pytest.mark.asyncio
async def test_scoring_combines_url_and_dom_reasons() -> None:
    result = await analyze_url(
        AnalysisRequest(
            url="http://verify-account.example.test/login",
            dom_features=DOMFeatures(
                has_password_field=True,
                num_forms=1,
                external_form_action=True,
                num_iframes=0,
                external_links_ratio=0.1,
                has_hidden_inputs=False,
            ),
        )
    )

    assert result.risk_score >= 35
    assert result.label in {"suspicious", "dangerous"}
    assert "Domain or path contains suspicious keywords" in result.reasons
    assert "Page contains a password field" in result.reasons
