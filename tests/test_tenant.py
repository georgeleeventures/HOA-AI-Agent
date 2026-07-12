"""Tests for tenant resolution and tenant-scoped web routes."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

from starlette.requests import Request

from app.tenant import TenantMiddleware
from app.web.routes import document_detail


class TestExtractSlug:
    def test_subdomain(self):
        assert TenantMiddleware._extract_slug("twinpeaks.housekeep.click") == "twinpeaks"

    def test_no_subdomain(self):
        assert TenantMiddleware._extract_slug("housekeep.click") is None

    def test_localhost(self):
        assert TenantMiddleware._extract_slug("localhost:8000") is None

    def test_localhost_with_subdomain(self):
        assert TenantMiddleware._extract_slug("twinpeaks.localhost") == "twinpeaks"

    def test_with_port(self):
        assert TenantMiddleware._extract_slug("twinpeaks.housekeep.click:443") == "twinpeaks"

    def test_empty(self):
        assert TenantMiddleware._extract_slug("") is None


class TestDocumentDetailTenantScope:
    @patch("app.web.routes.templates.TemplateResponse")
    @patch("app.web.routes.get_pool", new_callable=AsyncMock)
    @patch("app.web.routes.get_current_user")
    @patch("app.documents.store.DocumentStore")
    def test_uses_session_hoa_id(
        self,
        mock_store_class,
        mock_get_current_user,
        mock_get_pool,
        mock_template_response,
    ):
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/documents/doc-1",
                "headers": [],
                "query_string": b"",
                "scheme": "https",
                "server": ("housekeep.click", 443),
            }
        )
        request.state.hoa_id = None
        mock_get_current_user.return_value = {"hoa_id": "hoa-1"}
        mock_get_pool.return_value = Mock()
        store = mock_store_class.return_value
        store.get_document = AsyncMock(return_value={"id": "doc-1"})

        asyncio.run(document_detail(request, "doc-1"))

        store.get_document.assert_awaited_once_with("doc-1", "hoa-1")
        mock_template_response.assert_called_once()
