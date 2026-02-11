"""Webhook signature verification and authentication."""

import hashlib
import hmac
from typing import Annotated

from fastapi import Header, HTTPException, Request

from aidw.env import get_settings


async def verify_webhook_signature(
    request: Request,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> bytes:
    """Verify GitHub webhook signature.

    Returns the raw body if signature is valid.
    Raises HTTPException if invalid.
    """
    settings = get_settings()

    if not settings.webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Missing signature header")

    body = await request.body()

    # Compute expected signature
    expected_sig = "sha256=" + hmac.new(
        settings.webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison
    if not hmac.compare_digest(expected_sig, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return body


def is_user_allowed(username: str) -> bool:
    """Check if a GitHub username is in the allowed list.

    Important: If the allowed_users list is empty, this returns False
    for all users (deny-by-default security posture). You must explicitly
    configure allowed users in config.yml.

    Args:
        username: GitHub username to check

    Returns:
        True if user is allowed, False otherwise
    """
    settings = get_settings()

    # If no allowed users configured, deny all
    if not settings.auth.allowed_users:
        return False

    return username in settings.auth.allowed_users
