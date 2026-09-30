from sqlalchemy import select

from src.api.errors import ApiError
from src.db import session_scope
from src.models.tables import AuditEvent, Incident


def get_audit(incident_id: str) -> dict:
    with session_scope() as session:
        incident = session.scalar(select(Incident).where(Incident.incident_id == incident_id))
        if incident is None:
            raise ApiError("INCIDENT_NOT_FOUND", "Incident was not found.", 404)
        rows = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.incident_id == incident.id)
            .order_by(AuditEvent.created_at, AuditEvent.id)
        ).all()
        return {
            "incident_id": incident_id,
            "items": [
                {
                    "action": row.action,
                    "actor": row.actor,
                    "metadata": row.event_metadata or {},
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ],
        }
