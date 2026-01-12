"""IP whitelisting middleware for remote API access control."""

import ipaddress
import logging
from typing import List, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce IP whitelisting for remote API access."""

    def __init__(
        self,
        allowed_ips: Optional[List[str]] = None,
        allowed_cidrs: Optional[List[str]] = None,
        allow_localhost: bool = True,
    ):
        """Initialize IP whitelist middleware.

        Args:
            allowed_ips: List of individual IP addresses to allow
            allowed_cidrs: List of CIDR blocks to allow (e.g., "192.168.1.0/24")
            allow_localhost: Whether to allow localhost connections
        """
        super().__init__()
        self.allowed_ips = set()
        self.allowed_cidrs = []
        self.allow_localhost = allow_localhost

        if allowed_ips:
            for ip_str in allowed_ips:
                try:
                    self.allowed_ips.add(ipaddress.ip_address(ip_str))
                except ValueError as e:
                    logger.warning(f"Invalid IP address {ip_str}: {e}")

        if allowed_cidrs:
            for cidr_str in allowed_cidrs:
                try:
                    self.allowed_cidrs.append(ipaddress.ip_network(cidr_str, strict=False))
                except ValueError as e:
                    logger.warning(f"Invalid CIDR block {cidr_str}: {e}")

        logger.info(
            f"IP whitelist middleware initialized: "
            f"{len(self.allowed_ips)} IPs, "
            f"{len(self.allowed_cidrs)} CIDRs, "
            f"allow_localhost={allow_localhost}"
        )

    async def dispatch(self, request: Request, call_next):
        """Process request and check IP whitelist.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response from next handler or raises HTTPException if IP not allowed
        """
        client_ip = self._get_client_ip(request)

        if not self._is_ip_allowed(client_ip):
            logger.warning(
                f"Blocked request from disallowed IP: {client_ip}, "
                f"path: {request.url.path}, "
                f"method: {request.method}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied from IP {client_ip}. Not in whitelist.",
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request.

        Checks X-Forwarded-For header for proxied requests.

        Args:
            request: Incoming request

        Returns:
            Client IP address as string
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"

    def _is_ip_allowed(self, ip_str: str) -> bool:
        """Check if IP address is allowed.

        Args:
            ip_str: IP address string

        Returns:
            True if IP is allowed, False otherwise
        """
        if ip_str == "unknown":
            logger.warning("Could not determine client IP")
            return False

        if self.allow_localhost and self._is_localhost(ip_str):
            return True

        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            logger.warning(f"Invalid IP address: {ip_str}")
            return False

        if ip in self.allowed_ips:
            return True

        for cidr in self.allowed_cidrs:
            if ip in cidr:
                return True

        return False

    def _is_localhost(self, ip_str: str) -> bool:
        """Check if IP is localhost.

        Args:
            ip_str: IP address string

        Returns:
            True if IP is localhost (127.0.0.1 or ::1)
        """
        try:
            ip = ipaddress.ip_address(ip_str)
            return ip.is_loopback
        except ValueError:
            return False
