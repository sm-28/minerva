"""
shared.models — Database model definitions (ORM / dataclasses).

Each model corresponds to a table in the database schema.
All models include the standard audit columns:
    created_by, created_on, last_updated_by, last_updated_on
"""

from .organization import Organization
from .business import Business
from .user import User
from .document import Document
from .ingestion_job import IngestionJob
