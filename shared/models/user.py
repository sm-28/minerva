"""
shared/models/user.py — Dashboard user model.

Table: public.users

Fields:
    id, email, name, org_id (FK → organizations.id),
    role ('org_admin' | 'business_admin' | 'viewer'), is_active
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Represents a row in public.users."""

    id: uuid.UUID
    email: str
    name: Optional[str]
    org_id: uuid.UUID
    role: str = "viewer"  # org_admin | business_admin | viewer
    is_active: bool = True

    # Audit columns
    created_by: Optional[uuid.UUID] = None
    created_on: Optional[datetime] = None
    last_updated_by: Optional[uuid.UUID] = None
    last_updated_on: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "User":
        return cls(
            id=record["id"],
            email=record["email"],
            name=record.get("name"),
            org_id=record["org_id"],
            role=record.get("role", "viewer"),
            is_active=record.get("is_active", True),
            created_by=record.get("created_by"),
            created_on=record.get("created_on"),
            last_updated_by=record.get("last_updated_by"),
            last_updated_on=record.get("last_updated_on"),
        )
