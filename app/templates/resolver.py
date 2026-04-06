"""
Template resolver — looks up a Template from Postgres by name or UUID.

Lookup strategy
---------------
1. If body.template looks like a UUID, query by id (owner-agnostic).
   This allows sharing templates across owners by ID link.
2. Otherwise, query by (owner, name) — owner-scoped by the requesting key's
   owner, so acme-corp cannot accidentally use bob-corp's named templates.

Phase 4: no Redis cache for templates. The table will be tiny and rarely
queried hot. Add caching if profiling ever shows it as a bottleneck.
"""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Template
from app.exceptions import NotFoundError

logger = structlog.get_logger()


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


async def resolve_template(
    name_or_id: str,
    owner: str,
    db: AsyncSession,
) -> Template:
    """
    Resolve a template reference from the inference request.

    Parameters
    ----------
    name_or_id  Value from body.template: either a UUID string or a name.
    owner       The requesting key's owner — used for name-based scoping.
    db          Active async DB session.

    Returns
    -------
    Template instance.

    Raises
    ------
    NotFoundError  If no matching template exists (404).
    """
    if _is_uuid(name_or_id):
        # UUID lookup — not owner-scoped (share by ID is intentional)
        result = await db.execute(
            select(Template).where(Template.id == uuid.UUID(name_or_id))
        )
        template = result.scalar_one_or_none()
        if template is not None:
            logger.debug("template_resolved_by_id", template_id=name_or_id)
            return template

    # Name lookup — owner-scoped (Phase 4: own namespace only)
    result = await db.execute(
        select(Template).where(
            Template.name == name_or_id,
            Template.owner == owner,
        )
    )
    template = result.scalar_one_or_none()

    if template is None:
        # Global template fallback — owner=NULL templates are seeded by admins
        # and readable by all keys. Priority: own-namespace → global → 404
        result = await db.execute(
            select(Template).where(
                Template.name == name_or_id,
                Template.owner.is_(None),
            )
        )
        template = result.scalar_one_or_none()

    if template is None:
        raise NotFoundError(f"Template '{name_or_id}' not found.")

    logger.debug(
        "template_resolved_by_name",
        template_name=name_or_id,
        owner=owner,
    )
    return template
