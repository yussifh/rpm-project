"""
NotificationService — generic per-user inbox items. Created internally by
other services (AlertService, future AppointmentService, etc.) as well as
exposed via a small self-service API (list mine, mark as read).
"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.notifications = NotificationRepository(db)

    def list_for_user(self, user_id: uuid.UUID, unread_only: bool = False) -> list[Notification]:
        return self.notifications.list_for_user(user_id, unread_only=unread_only)

    def create(self, user_id: uuid.UUID, title: str, message: str, notification_type: str) -> Notification:
        notification = Notification(
            user_id=user_id, title=title, message=message, notification_type=notification_type
        )
        return self.notifications.create(notification)

    def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        notification = self.notifications.get_by_id(notification_id)
        if not notification or notification.user_id != user_id:
            raise NotFoundError("Notification", str(notification_id))
        notification.is_read = True
        return self.notifications.save(notification)
