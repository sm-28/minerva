"""
shared/models/business.py — Business (tenant) model.

Table: public.businesses

Fields:
    id, org_id (FK → organizations.id), name, slug, schema_name,
    industry, allowed_domains (JSONB), allowed_ips (JSONB), is_active

Notes:
    - This is a global table that exists in the public schema.
    - A Business is a tenant within an Organization.
    - Each Business maps to its own PostgreSQL schema: tenant_<business_slug>.
    - This schema isolation ensures complete data and knowledge-base separation
      between businesses, even those belonging to the same Organization.
    - One Organization can own many Businesses (e.g. "Sales Bot", "Support Bot").
    - FAISS vector index: one per Business, scoped to that Business's documents.
    - S3 paths are scoped per Business:
        s3://<bucket>/businesses/<business_id>/...
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Business:
    """Represents a row in public.businesses."""

    id: uuid.UUID
    org_id: uuid.UUID                           # FK → public.organizations.id
    name: str
    slug: str                                   # e.g. 'acme-sales-bot'
    schema_name: str                            # e.g. 'tenant_acmesalesbot'
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
    def from_record(cls, record: dict) -> "Business":
        return cls(
            id=record["id"],
            org_id=record["org_id"],
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
