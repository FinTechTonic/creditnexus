"""Middleware package initialization."""

from app.middleware.ip_whitelist import IPWhitelistMiddleware

__all__ = ["IPWhitelistMiddleware"]
