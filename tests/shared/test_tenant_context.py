"""
tests/shared/test_tenant_context.py — Tests for tenant schema routing utilities.

Covers:
    - get_tenant_schema() returns correct schema name
    - get_tenant_schema() raises ValueError on invalid slug
    - set_tenant_schema() calls conn.execute with correct SQL
    - reset_to_public() calls conn.execute to reset search_path
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from shared.db.tenant_context import (
    get_tenant_schema,
    set_tenant_schema,
    reset_to_public,
)


class TestGetTenantSchema:
    def test_simple_slug(self):
        assert get_tenant_schema("acme") == "tenant_acme"

    def test_slug_with_numbers(self):
        assert get_tenant_schema("client123") == "tenant_client123"

    def test_slug_with_underscores(self):
        assert get_tenant_schema("my_company") == "tenant_my_company"

    def test_uppercase_slug_normalised(self):
        assert get_tenant_schema("ACME") == "tenant_acme"

    def test_slug_with_leading_trailing_spaces(self):
        assert get_tenant_schema("  acme  ") == "tenant_acme"

    def test_empty_slug_raises(self):
        with pytest.raises(ValueError, match="Invalid client slug"):
            get_tenant_schema("")

    def test_slug_with_hyphen_raises(self):
        with pytest.raises(ValueError, match="Invalid client slug"):
            get_tenant_schema("my-company")

    def test_slug_with_dot_raises(self):
        with pytest.raises(ValueError, match="Invalid client slug"):
            get_tenant_schema("my.company")

    def test_slug_with_sql_injection_raises(self):
        with pytest.raises(ValueError, match="Invalid client slug"):
            get_tenant_schema("acme; DROP TABLE documents;--")


class TestSetTenantSchema:
    @pytest.mark.asyncio
    async def test_executes_set_search_path(self):
        mock_conn = AsyncMock()
        await set_tenant_schema(mock_conn, "tenant_acme")
        mock_conn.execute.assert_called_once_with(
            "SET search_path TO tenant_acme, public"
        )

    @pytest.mark.asyncio
    async def test_unsafe_schema_name_raises(self):
        mock_conn = AsyncMock()
        with pytest.raises(ValueError, match="Unsafe schema name"):
            await set_tenant_schema(mock_conn, "tenant_acme; DROP TABLE users;--")


class TestResetToPublic:
    @pytest.mark.asyncio
    async def test_executes_reset(self):
        mock_conn = AsyncMock()
        await reset_to_public(mock_conn)
        mock_conn.execute.assert_called_once_with("SET search_path TO public")
