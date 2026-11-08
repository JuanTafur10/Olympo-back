"""Pruebas de validaciones que protegen la creacion de proyectos."""

from fastapi import BackgroundTasks

from api_server import ProyectoRequest, crear_proyecto


def test_rejects_negative_budget_without_touching_database():
    payload = ProyectoRequest(
        propietario_id="propietario-invalido",
        titulo="Proyecto critico",
        presupuesto=-1,
    )

    result = crear_proyecto(payload, BackgroundTasks())

    assert result == {"ok": False, "mensaje": "El presupuesto no puede ser negativo"}


def test_rejects_budget_above_allowed_limit():
    payload = ProyectoRequest(
        propietario_id="propietario-invalido",
        titulo="Proyecto critico",
        presupuesto=1_000_000_000_000,
    )

    result = crear_proyecto(payload, BackgroundTasks())

    assert result["ok"] is False
    assert "presupuesto máximo permitido" in result["mensaje"]


def test_rejects_unknown_project_state():
    payload = ProyectoRequest(
        propietario_id="propietario-invalido",
        titulo="Proyecto critico",
        presupuesto=100,
        estado="borrador",
    )

    result = crear_proyecto(payload, BackgroundTasks())

    assert result == {"ok": False, "mensaje": "Estado inválido. Usa activo o inactivo"}

