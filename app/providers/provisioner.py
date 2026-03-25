"""
OpenRouter key provisioner.

Wraps the OpenRouter Management API to create, disable, and delete
provisioned API keys on behalf of RouterV owners.

Management keys are separate credentials (not regular API keys) that
can only perform key CRUD operations — they cannot make completions.
Create one at: https://openrouter.ai/settings/management-keys

All functions are fail-soft: on any error they return None / False and
log a warning rather than raising.  Callers must handle None returns and
fall back to the system default key.

Auto-provisioning flow (triggered on admin key creation):
  1.  POST /api/v1/keys  →  { key: "<plaintext>", data: { hash: "..." } }
  2.  Store plaintext in GCP Secret Manager  →  get secret_ref
  3.  Write ProviderKey row  (owner, or_key_hash, secret_ref)
  4.  Link api_keys.provider_key_id  →  new ProviderKey.id

Key rotation flow (triggered on admin /rotate):
  1.  POST /api/v1/keys  →  new key + hash
  2.  Store in Secret Manager (new version)
  3.  PATCH old ProviderKey.secret_ref  →  new version path
  4.  DELETE /api/v1/keys/{old_hash}  →  deactivate old key on OpenRouter
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

_OR_KEYS_URL = "https://openrouter.ai/api/v1/keys"


@dataclass
class ProvisionedKey:
    """Result of a successful key creation on OpenRouter."""

    plaintext: str   # sk-or-v1-... — store in Secret Manager immediately
    or_hash: str     # used for subsequent PATCH / DELETE calls


def _mgmt_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.openrouter_management_key}",
        "Content-Type": "application/json",
    }


def _provisioning_enabled() -> bool:
    """
    Return True only when both the management key and GCP project are
    configured.  In local dev neither is set, so auto-provisioning is
    silently skipped and the system default key is used.
    """
    return bool(settings.openrouter_management_key and settings.gcp_project_id)


async def create_or_key(
    owner: str,
    *,
    limit_usd: float | None = None,
    limit_reset: str | None = "monthly",
) -> ProvisionedKey | None:
    """
    Create a new API key on OpenRouter for a given owner.

    Parameters
    ----------
    owner:
        RouterV owner label — used as the key name so it's identifiable
        in the OpenRouter dashboard.
    limit_usd:
        Optional USD spending limit.  Pass the owner's spend_cap_usd so
        OpenRouter enforces a hard cap in addition to RouterV's soft cap.
    limit_reset:
        When to reset the OpenRouter limit counter: "daily", "weekly",
        "monthly", or None.  Defaults to "monthly".

    Returns
    -------
    ProvisionedKey | None
        The plaintext key + OpenRouter hash, or None on any failure.
    """
    if not _provisioning_enabled():
        logger.debug(
            "provisioner_skipped",
            reason="management key or GCP project not configured",
            owner=owner,
        )
        return None

    body: dict = {"name": f"routerv:{owner}"}
    if limit_usd is not None:
        body["limit"] = limit_usd
        body["limit_reset"] = limit_reset

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                _OR_KEYS_URL,
                json=body,
                headers=_mgmt_headers(),
            )
            response.raise_for_status()
            data = response.json()

        plaintext: str = data["key"]
        or_hash: str = data["data"]["hash"]
        logger.info("or_key_provisioned", owner=owner, or_hash=or_hash[:12] + "...")
        return ProvisionedKey(plaintext=plaintext, or_hash=or_hash)

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "or_key_provision_failed",
            owner=owner,
            status=exc.response.status_code,
            body=exc.response.text[:200],
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("or_key_provision_error", owner=owner, error=str(exc))
        return None


async def disable_or_key(or_hash: str) -> bool:
    """
    Disable (but do not delete) a key on OpenRouter.

    Used during rotation: the old key is disabled before the new one is
    confirmed working.  A disabled key can be re-enabled via PATCH.

    Returns True on success.
    """
    if not _provisioning_enabled():
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(
                f"{_OR_KEYS_URL}/{or_hash}",
                json={"disabled": True},
                headers=_mgmt_headers(),
            )
            response.raise_for_status()
        logger.info("or_key_disabled", or_hash=or_hash[:12] + "...")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("or_key_disable_failed", or_hash=or_hash[:12] + "...", error=str(exc))
        return False


async def delete_or_key(or_hash: str) -> bool:
    """
    Permanently delete a key from OpenRouter.

    Called after rotation is confirmed — removes the old key so it can
    never be used again.  This is irreversible.

    Returns True on success.
    """
    if not _provisioning_enabled():
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(
                f"{_OR_KEYS_URL}/{or_hash}",
                headers=_mgmt_headers(),
            )
            response.raise_for_status()
        logger.info("or_key_deleted", or_hash=or_hash[:12] + "...")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("or_key_delete_failed", or_hash=or_hash[:12] + "...", error=str(exc))
        return False


async def update_or_key_limit(or_hash: str, limit_usd: float, limit_reset: str = "monthly") -> bool:
    """
    Update the spending limit on an existing OpenRouter key.

    Called when an owner's RouterV spend_cap_usd is changed so both
    enforcement layers stay in sync.

    Returns True on success.
    """
    if not _provisioning_enabled():
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(
                f"{_OR_KEYS_URL}/{or_hash}",
                json={"limit": limit_usd, "limit_reset": limit_reset},
                headers=_mgmt_headers(),
            )
            response.raise_for_status()
        logger.info("or_key_limit_updated", or_hash=or_hash[:12] + "...", limit=limit_usd)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("or_key_limit_update_failed", or_hash=or_hash[:12] + "...", error=str(exc))
        return False
