"""
Audit log schema — read-only (there is no create/update schema, since
audit logs are only ever written internally by AuditService, never via
a direct API request body).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    ip_address: str | None
    extra_metadata: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
