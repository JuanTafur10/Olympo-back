"""Pruebas unitarias de autenticacion y clasificacion de riesgos."""

import pytest
from starlette.requests import Request

from api_server import _obtener_token_bearer
from app.controller.ares_cache_controller import _calcular_tipo_riesgo


def request_with_authorization(value: str | None) -> Request:
    headers = [] if value is None else [(b"authorization", value.encode())]
    return Request({"type": "http", "headers": headers})


def test_extracts_bearer_token_case_insensitively():
    request = request_with_authorization("Bearer token-de-prueba")

    assert _obtener_token_bearer(request) == "token-de-prueba"


@pytest.mark.parametrize("authorization", [None, "Basic token", "Bearer "])
def test_rejects_missing_or_invalid_bearer_token(authorization):
    with pytest.raises(ValueError, match="autenticación con token Bearer"):
        _obtener_token_bearer(request_with_authorization(authorization))


@pytest.mark.parametrize(
    ("probabilidad", "impacto", "expected"),
    [(1, 1, "bajo"), (2, 3, "medio"), (4, 3, "alto")],
)
def test_classifies_risk_from_probability_and_impact(probabilidad, impacto, expected):
    assert _calcular_tipo_riesgo(probabilidad, impacto) == expected

