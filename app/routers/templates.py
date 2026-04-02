"""
Template management — POST/GET/PATCH/DELETE /v1/templates

Control plane endpoint — requires a Supabase JWT (dashboard session),
NOT an inference key.  This keeps the data plane (rsk_ keys / completions)
cleanly separated from the control plane (templates, configuration).

Auth:    Authorization: Bearer <supabase-jwt>
Scoping: all operations are restricted to templates owned by identity.owner

Create  POST   /v1/templates
List    GET    /v1/templates
Get     GET    /v1/templates/{id}
Update  PATCH  /v1/templates/{id}
Delete  DELETE /v1/templates/{id}
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_any_auth_owner
from app.db.models import Template
from app.db.session import get_db_session
from app.exceptions import NotFoundError

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/templates", tags=["templates"])


# ── Pydantic I/O ──────────────────────────────────────────────────────────────

class CreateTemplateRequest(BaseModel):
    name: str
    description: str | None = None
    system: str | None = None
    messages: list[dict] | None = None   # [{role, content}, ...]
    model: str | None = None
    params: dict | None = None
    variables: list[str] | None = None   # declared slot names for documentation


class UpdateTemplateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    system: str | None = None
    messages: list[dict] | None = None
    model: str | None = None
    params: dict | None = None
    variables: list[str] | None = None


class TemplateSummary(BaseModel):
    id: str
    name: str
    owner: str
    description: str | None
    system: str | None
    messages: list[dict] | None
    model: str | None
    params: dict | None
    variables: list[str] | None
    created_at: str
    updated_at: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=TemplateSummary, status_code=201)
async def create_template(
    body: CreateTemplateRequest,
    owner: str = Depends(get_any_auth_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a template scoped to the authenticated user's owner."""
    template = Template(
        name=body.name,
        owner=owner,
        description=body.description,
        system=body.system,
        messages=body.messages,
        model=body.model,
        params=body.params,
        variables=body.variables,
    )
    db.add(template)
    try:
        await db.flush()
        await db.refresh(template)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"A template named '{body.name}' already exists for owner '{owner}'.",
        )

    logger.info(
        "template_created",
        template_id=str(template.id),
        name=template.name,
        owner=template.owner,
    )
    return _to_summary(template)


@router.get("", response_model=list[TemplateSummary])
async def list_templates(
    owner: str = Depends(get_any_auth_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """List all templates belonging to the authenticated user's owner."""
    result = await db.execute(
        select(Template)
        .where(Template.owner == owner)
        .order_by(Template.created_at.desc())
    )
    return [_to_summary(t) for t in result.scalars().all()]


@router.get("/{template_id}", response_model=TemplateSummary)
async def get_template(
    template_id: str,
    owner: str = Depends(get_any_auth_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Get a single template by UUID. Must belong to the caller's owner."""
    template = await _get_own_or_404(db, template_id, owner)
    return _to_summary(template)


@router.patch("/{template_id}", response_model=TemplateSummary)
async def update_template(
    template_id: str,
    body: UpdateTemplateRequest,
    owner: str = Depends(get_any_auth_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Update a template. Only the owning user can edit."""
    template = await _get_own_or_404(db, template_id, owner)

    if body.name is not None:
        template.name = body.name
    if body.description is not None:
        template.description = body.description
    if body.system is not None:
        template.system = body.system
    if body.messages is not None:
        template.messages = body.messages
    if body.model is not None:
        template.model = body.model
    if body.params is not None:
        template.params = body.params
    if body.variables is not None:
        template.variables = body.variables

    try:
        await db.flush()
        await db.refresh(template)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"A template named '{body.name}' already exists for owner '{owner}'.",
        )

    logger.info(
        "template_updated",
        template_id=str(template.id),
        name=template.name,
        owner=template.owner,
    )
    return _to_summary(template)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    owner: str = Depends(get_any_auth_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Hard delete. Only the owning user can delete."""
    template = await _get_own_or_404(db, template_id, owner)
    await db.delete(template)
    logger.info(
        "template_deleted",
        template_id=str(template.id),
        name=template.name,
        owner=template.owner,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_own_or_404(
    db: AsyncSession,
    template_id: str,
    owner: str,
) -> Template:
    try:
        uid = uuid.UUID(template_id)
    except ValueError:
        raise NotFoundError(f"Template '{template_id}' not found.")

    result = await db.execute(
        select(Template).where(Template.id == uid, Template.owner == owner)
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise NotFoundError(f"Template '{template_id}' not found.")
    return template


def _to_summary(t: Template) -> TemplateSummary:
    return TemplateSummary(
        id=str(t.id),
        name=t.name,
        owner=t.owner,
        description=t.description,
        system=t.system,
        messages=t.messages,
        model=t.model,
        params=t.params,
        variables=t.variables,
        created_at=t.created_at.isoformat(),
        updated_at=t.updated_at.isoformat(),
    )
