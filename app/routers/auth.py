"""
Auth endpoints — POST /v1/auth/send-otp, POST /v1/auth/verify-otp

Proxies OTP send/verify to Supabase Auth REST API, then upserts the User
record in the local DB on successful verification.

Requires SUPABASE_URL and SUPABASE_ANON_KEY to be set.
"""

import asyncio
import structlog
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import User
from app.db.session import get_db_session

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/auth", tags=["auth"])


# ── Pydantic I/O ──────────────────────────────────────────────────────────────

class SendOtpRequest(BaseModel):
    email: str
    utmParams: str | None = None


class VerifyOtpRequest(BaseModel):
    email: str
    otp: str


class _SupabaseUser(BaseModel):
    id: str
    email: str
    user_metadata: dict = {}


class _SupabaseSession(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: int
    token_type: str
    user: _SupabaseUser


class VerifyOtpResponse(BaseModel):
    session: _SupabaseSession


# ── Helpers ───────────────────────────────────────────────────────────────────

def _supabase_headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_anon_key,
        "Content-Type": "application/json",
    }


_DEV_ALLOWED_DOMAINS = {"fleapo.com", "tagmango.com", "aifiesta.ai", "meshapi.ai"}


def _check_supabase_configured() -> None:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=503, detail="Auth service not configured")


def _check_email_allowed(email: str) -> None:
    if settings.env != "dev":
        return
    domain = email.rsplit("@", 1)[-1].lower()
    if domain not in _DEV_ALLOWED_DOMAINS:
        raise HTTPException(status_code=403, detail="Email domain not allowed in dev environment")


# ── Email ─────────────────────────────────────────────────────────────────────

async def _send_welcome_email(email: str) -> None:
    if not settings.mailmodo_webhook_url:
        return
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                settings.mailmodo_webhook_url,
                json={"email": email, "data": {}},
                timeout=10.0,
            )
        if resp.status_code not in (200, 201):
            logger.warning("mailmodo_welcome_failed", status=resp.status_code, email=email, body=resp.text)
        else:
            logger.info("mailmodo_welcome_sent", email=email)
    except Exception:
        logger.exception("mailmodo_welcome_error", email=email)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/send-otp")
async def send_otp(body: SendOtpRequest) -> dict[str, str]:
    """
    Send a 6-digit OTP to the given email address via Supabase Auth.
    Creates the user in Supabase if they don't exist yet.
    """
    _check_supabase_configured()
    _check_email_allowed(body.email)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.supabase_url}/auth/v1/otp",
            json={"email": body.email, "create_user": True},
            headers=_supabase_headers(),
            timeout=10.0,
        )

    if resp.status_code not in (200, 204):
        logger.warning(
            "supabase_send_otp_failed",
            status=resp.status_code,
            email=body.email,
            body=resp.text,
        )
        raise HTTPException(status_code=502, detail="Failed to send OTP")

    return {"message": "OTP sent"}


@router.post("/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(
    body: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db_session),
) -> VerifyOtpResponse:
    """
    Verify the 6-digit OTP. On success:
    - Returns a Supabase session (access_token, refresh_token, user).
    - Upserts the User record in the local DB.
    """
    _check_supabase_configured()
    _check_email_allowed(body.email)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.supabase_url}/auth/v1/verify",
            json={"type": "email", "email": body.email, "token": body.otp},
            headers=_supabase_headers(),
            timeout=10.0,
        )

    if resp.status_code != 200:
        logger.warning(
            "supabase_verify_otp_failed",
            status=resp.status_code,
            email=body.email,
            body=resp.text,
        )
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    data = resp.json()
    supabase_user = data.get("user") or {}

    session = _SupabaseSession(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=data.get("expires_at", 0),
        token_type=data.get("token_type", "bearer"),
        user=_SupabaseUser(
            id=supabase_user["id"],
            email=supabase_user["email"],
            user_metadata=supabase_user.get("user_metadata") or {},
        ),
    )

    # Upsert the user profile in our DB
    if settings.database_url:
        result = await db.execute(select(User).where(User.id == session.user.id))
        user = result.scalar_one_or_none()

        if user is None:
            db.add(User(id=session.user.id, email=session.user.email))
            asyncio.create_task(_send_welcome_email(session.user.email))
        else:
            user.email = session.user.email

        await db.flush()
        logger.info("user_upserted", user_id=session.user.id, email=session.user.email)

    return VerifyOtpResponse(session=session)
