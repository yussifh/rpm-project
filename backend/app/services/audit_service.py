"""
AuditService — the single entry point every other service calls to record
a state-changing action. Centralizing it here (rather than each service
writing directly to AuditLogRepository) means the log FORMAT (action naming,
what goes in extra_metadata) stays consistent system-wide.

Design decision — where this is wired in: rather than instrumenting every
single write endpoint (which would bloat every service with near-identical
boilerplate), this is wired into the highest-value, most compliance-relevant
actions: admin user management (account creation/activation), medication
logging, and alert lifecycle changes. The pattern (one `audit.log(...)` call) is trivial to extend to
any other service — it's a placement decision, not a technical limitation.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self.logs = AuditLogRepository(db)

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str | uuid.UUID | None,
        user_id: uuid.UUID | None = None,
        metadata: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            extra_metadata=metadata,
            ip_address=ip_address,
        )
        return self.logs.create(entry)
