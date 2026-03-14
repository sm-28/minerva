"""
shared/models/client.py — Client (tenant) model.

Table: public.clients

Fields:
    id, name, slug, schema_name, industry,
    allowed_domains (JSONB), allowed_ips (JSONB), is_active

This is a global table — exists in the public schema.
Each client maps to a tenant schema: tenant_<slug>.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Client:
    """Represents a row in public.clients."""

    id: uuid.UUID
    name: str
    slug: str
    schema_name: str                        # e.g. 'tenant_acme'
    industry: Optional[str] = None
    allowed_domains: list[str] = field(default_factory=list)
    allowed_ips: list[str] = field(default_factory=list)
    is_active: bool = True

    # Audit columns
    created_by: Optional[uuid.UUID] = None
    created_on: Optional[datetime] = None
    last_updated_by: Optional[uuid.UUID] = None
    last_updated_on: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Client":
        return cls(
            id=record["id"],
            name=record["name"],
            slug=record["slug"],
            schema_name=record["schema_name"],
            industry=record.get("industry"),
            allowed_domains=record.get("allowed_domains") or [],
            allowed_ips=record.get("allowed_ips") or [],
            is_active=record.get("is_active", True),
            created_by=record.get("created_by"),
            created_on=record.get("created_on"),
            last_updated_by=record.get("last_updated_by"),
            last_updated_on=record.get("last_updated_on"),
        )
