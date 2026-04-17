"""Tests for tenant middleware subdomain extraction."""

from app.tenant import TenantMiddleware


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
