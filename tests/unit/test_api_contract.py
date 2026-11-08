"""Pruebas del contrato HTTP y la documentacion publica de la API."""

from api_server import app, health_check


def test_swagger_docs_are_accessible():
    assert app.docs_url == "/docs"
    assert any(getattr(route, "path", None) == "/docs" for route in app.routes)


def test_openapi_schema_is_accessible_and_describes_api():
    schema = app.openapi()
    assert schema["info"]["title"] == "Olympo API"
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]


def test_health_endpoint_returns_backend_status():
    assert health_check() == {"ok": True, "servicio": "backend-olympo"}

