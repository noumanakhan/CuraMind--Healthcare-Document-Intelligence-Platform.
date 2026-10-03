"""Backward-compatible audit helper; business operations belong to services."""

from app.services.audit import write_audit

__all__ = ["write_audit"]