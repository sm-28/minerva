"""
shared/models/organization.py — Organization (top-level billing entity) model.

Table: public.organizations

Fields:
    id, name, is_active

Notes:
    - This is a global table that exists in the public schema.
    - An Organization is the parent billing/contractual entity (formerly 'clients').
    - Each Organization can own multiple Businesses.
    - Billing is aggregated across all Businesses within an Organization.
    - API keys are scoped to individual Businesses (not Organizations).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Organization:
    """Represents a row in public.organizations."""

    id: uuid.UUID
    name: str
    is_active: bool = True

    # Audit columns
    created_by: Optional[uuid.UUID] = None
    created_on: Optional[datetime] = None
    last_updated_by: Optional[uuid.UUID] = None
    last_updated_on: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Organization":
        return cls(
            id=record["id"],
            name=record["name"],
            is_active=record.get("is_active", True),
            created_by=record.get("created_by"),
            created_on=record.get("created_on"),
            last_updated_by=record.get("last_updated_by"),
            last_updated_on=record.get("last_updated_on"),
        )
