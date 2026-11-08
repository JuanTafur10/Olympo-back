from __future__ import annotations

from typing import Iterable

from .firebase_conection import firestore_db


_COLECCION = "tickets_soporte"


def _normalizar_ticket(ticket: dict) -> dict:
    return {
        "id": ticket.get("id"),
        "usuario_id": ticket.get("usuario_id"),
        "categoria": ticket.get("categoria"),
        "prioridad": ticket.get("prioridad"),
        "canal": ticket.get("canal"),
        "asunto": ticket.get("asunto"),
        "descripcion": ticket.get("descripcion"),
        "adjuntar_contexto": ticket.get("adjuntar_contexto"),
        "estado": ticket.get("estado"),
        "creado_en": ticket.get("creado_en"),
        "actualizado_en": ticket.get("actualizado_en"),
        "asignado_a": ticket.get("asignado_a"),
        "notas_internas": ticket.get("notas_internas"),
    }


def _firestore_disponible() -> bool:
    return bool(getattr(firestore_db, "collection", None))


def sincronizar_ticket_firestore(ticket: dict | None) -> None:
    if not ticket or not _firestore_disponible():
        return

    ticket_id = str(ticket.get("id") or "").strip()
    if not ticket_id:
        return

    try:
        firestore_db.collection(_COLECCION).document(ticket_id).set(_normalizar_ticket(ticket), merge=True)
    except Exception as exc:
        print(f"[Tickets][Firestore] No se pudo sincronizar el ticket {ticket_id}: {exc}")


def sincronizar_tickets_firestore(tickets: Iterable[dict] | None) -> None:
    if not tickets or not _firestore_disponible():
        return

    try:
        batch = firestore_db.batch()
        procesados = 0
        for ticket in tickets:
            if not ticket:
                continue
            ticket_id = str(ticket.get("id") or "").strip()
            if not ticket_id:
                continue
            batch.set(firestore_db.collection(_COLECCION).document(ticket_id), _normalizar_ticket(ticket), merge=True)
            procesados += 1

        if procesados > 0:
            batch.commit()
    except Exception as exc:
        print(f"[Tickets][Firestore] No se pudo sincronizar el lote de tickets: {exc}")
