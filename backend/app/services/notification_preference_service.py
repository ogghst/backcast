"""Notification preference service.

Merges the static registry defaults with per-user ``UserNotificationPreference``
overrides and applies bulk upserts. Mirrors the ``Service(db_session)``
constructor style of :class:`NotificationService`.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notifications.registry import (
    REGISTRY,
    ChannelKind,
    NotificationCategory,
    category_for_code,
)
from app.models.domain.notification_preference import UserNotificationPreference
from app.models.schemas.notification import (
    NotificationCategoryPreferences,
    NotificationPreferenceEntry,
    NotificationPreferencesResponse,
)

# Category display labels (order roughly matches registry insertion order).
_CATEGORY_LABELS: dict[NotificationCategory, str] = {
    NotificationCategory.CHANGE_ORDER: "Change Orders",
    NotificationCategory.AGENT: "Agents",
    NotificationCategory.PROJECT: "Project",
    NotificationCategory.DOCUMENT: "Documents",
    NotificationCategory.BRANCH: "Branches",
    NotificationCategory.SYSTEM: "System",
}


class NotificationPreferenceService:
    """Read/merge and upsert per-user notification preferences."""

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            db_session: Async database session for queries.
        """
        self._db = db_session

    async def get_for_user(self, user_id: UUID) -> NotificationPreferencesResponse:
        """Return merged default + override preferences for *user_id*.

        Defaults come from :data:`REGISTRY` (each type's ``default_channels``
        are enabled); the user's ``UserNotificationPreference`` rows override
        the enabled flag for specific (event_type, channel) cells.

        Args:
            user_id: UUID of the user.

        Returns:
            A :class:`NotificationPreferencesResponse` grouped by category.
        """
        overrides = await self._load_overrides(user_id)

        # event_type -> {channel: enabled}, seeded from registry defaults.
        cells: dict[str, dict[str, bool]] = {}
        for code, type_def in REGISTRY.items():
            channel_map: dict[str, bool] = {
                channel.value: True for channel in type_def.default_channels
            }
            cells[code] = channel_map

        # Apply user overrides on top of defaults.
        for pref in overrides:
            cells.setdefault(pref.event_type, {})[pref.channel] = pref.enabled

        # Group by category (registry-driven), preserving registry order.
        grouped: dict[NotificationCategory, list[tuple[str, dict[str, bool]]]] = (
            defaultdict(list)
        )
        category_order: list[NotificationCategory] = []
        for code in REGISTRY:
            cat = category_for_code(code)
            grouped[cat].append((code, cells.get(code, {})))
            if cat not in category_order:
                category_order.append(cat)

        categories: list[NotificationCategoryPreferences] = []
        for cat in category_order:
            entries: list[NotificationPreferenceEntry] = []
            for code, channel_map in grouped[cat]:
                for channel, enabled in channel_map.items():
                    entries.append(
                        NotificationPreferenceEntry(
                            event_type=code, channel=channel, enabled=enabled
                        )
                    )
            categories.append(
                NotificationCategoryPreferences(
                    category=cat.value,
                    label=_CATEGORY_LABELS.get(cat, cat.value),
                    entries=entries,
                )
            )

        return NotificationPreferencesResponse(categories=categories)

    async def update_for_user(
        self,
        user_id: UUID,
        changes: list[NotificationPreferenceEntry],
    ) -> None:
        """Upsert preference cells for *user_id*.

        Each ``(user_id, event_type, channel)`` row is inserted or has its
        ``enabled`` flag updated.

        Args:
            user_id: UUID of the user.
            changes: Cells to upsert.
        """
        if not changes:
            return

        rows = [
            {
                "user_id": user_id,
                "event_type": c.event_type,
                "channel": c.channel,
                "enabled": c.enabled,
            }
            for c in changes
        ]
        stmt = pg_insert(UserNotificationPreference).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_notif_pref_user_type_channel",
            set_={"enabled": stmt.excluded.enabled},
        )
        await self._db.execute(stmt)
        await self._db.flush()

    async def _load_overrides(self, user_id: UUID) -> list[UserNotificationPreference]:
        """Load all preference overrides for *user_id* ordered by event_type."""
        stmt = (
            select(UserNotificationPreference)
            .where(UserNotificationPreference.user_id == user_id)
            .order_by(UserNotificationPreference.event_type)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())


__all__ = [
    "ChannelKind",
    "NotificationPreferenceService",
]
