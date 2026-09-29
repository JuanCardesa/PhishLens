"""Shared scoring contract, mirror of extension/src/utils/scoring-contract.test.ts.

Both this file and the TypeScript mirror load contracts/scoring-vectors.json and
assert the URL and DOM scorers produce the per-category scores and reason strings
recorded there. The scoring logic is reimplemented in two languages; a weight or
reason wording changed on only one side fails on that side. Edit the JSON and both
implementations together.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from app.schemas.analysis import DOMFeatures
from app.services.feature_extractor import extract_url_features
from app.services.scoring_service import (
    _score_dom,
    _score_url,
    label_from_score,
    scale_heuristic_score,
)

_CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "scoring-vectors.json"
_CONTRACT = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
_DOM_DEFAULTS: dict[str, Any] = _CONTRACT["dom_defaults"]
_VECTORS: list[dict[str, Any]] = _CONTRACT["vectors"]


@pytest.mark.parametrize("vector", _VECTORS, ids=[v["name"] for v in _VECTORS])
def test_scoring_contract(vector: dict[str, Any]) -> None:
    url_features = extract_url_features(vector["url"])
    url_score, url_reasons = _score_url(url_features)

    dom_features = DOMFeatures(**{**_DOM_DEFAULTS, **vector["dom"]})
    dom_score, dom_reasons = _score_dom(dom_features)

    assert url_score == vector["url_score"]
    assert url_reasons == vector["url_reasons"]
    assert dom_score == vector["dom_score"]
    assert dom_reasons == vector["dom_reasons"]

    heuristic_score = scale_heuristic_score(url_score, dom_score)
    assert heuristic_score == vector["heuristic_score"]
    assert label_from_score(heuristic_score) == vector["label"]
