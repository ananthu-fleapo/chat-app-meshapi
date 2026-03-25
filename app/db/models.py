"""
ORM models for RouterV.

Phase 2: api_keys — auth + config defaults.
Phase 3: adds rpm_limit, rpd_limit, spend_cap_usd to api_keys.
Phase 4: templates — system prompt + messages with {{variable}} substitution.
Phase 5: usage_events — append-only per-request log (tokens, cost, latency).
Phase 6: provider_keys — per-owner upstream API key references (GCP Secret Manager).
         api_keys.provider_key_id — links a RouterV key to its owner's provider key.
Future phases add: sessions, organizations.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ApiKey(Base):
    """
    A RouterV-issued API key.

    The plaintext key (rsk_<ULID>) is generated once and returned to the
    caller. Only its SHA-256 hash is stored here — if the DB is leaked,
    the hashes are worthless without the plaintext.

    Columns
    -------
    key_hash        SHA-256(plaintext_key) as hex digest
    owner           Human label for auditing: "acme-prod", "bob-dev", etc.
                    Not a FK — a separate orgs table arrives in a later phase.
    status          "active" | "suspended". Suspended keys get 403.
    default_model   Falls back to this if the caller omits model.
    default_params  JSONB of inference defaults, e.g. {"temperature": 0.7}.
                    Merged under request params; request always wins.
    meta            Arbitrary owner metadata. Not used by the router.
    rpm_limit       Max requests/minute. NULL → system default (Settings.default_rpm).
    rpd_limit       Max requests/day.    NULL → system default (Settings.default_rpd).
    spend_cap_usd   Max cumulative spend. NULL → no cap. Enforced in Phase 5.
    """

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    key_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    owner: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active", index=True)
    default_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Phase 3 — rate limits + spend cap
    rpm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpd_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spend_cap_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)

    # Phase 6 — per-owner upstream provider key.
    # NULL → system default (settings.openrouter_api_key).
    # Non-null → look up ProviderKey row for this owner's upstream key.
    # Not a DB-level FK; integrity enforced at app layer.
    provider_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Timestamps — set by the DB; onupdate handled by application layer for now.
    # Phase X: replace onupdate with a Postgres trigger for safety.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} owner={self.owner!r} status={self.status!r}>"


class Template(Base):
    """
    A reusable prompt template with {{variable}} substitution slots.

    Columns
    -------
    name         Human-readable identifier, unique per owner.
                 Used in the request as body.template = "my-template-name".
    owner        Matches api_key.owner — templates are owner-scoped.
    description  Optional human note, not forwarded to the model.
    system       System prompt text. May contain {{var}} placeholders.
                 Rendered and prepended as role=system before body.messages.
    messages     JSONB list of {role, content} base turns with {{vars}}.
                 Inserted between the system message and body.messages.
    model        Lowest-priority model suggestion. Overridden by key.default_model
                 or the request's explicit model field.
    params       JSONB inference defaults (temperature, max_tokens, …).
                 Lowest priority — request wins, then key defaults, then these.
    variables    JSONB list of declared slot names, e.g. ["language", "tone"].
                 Used for documentation; missing required vars raise 422 at
                 render time regardless of whether they're declared here.

    Priority order (highest → lowest) for model + params:
        request body  →  key.default_*  →  template.model / template.params
    """

    __tablename__ = "templates"
    __table_args__ = (
        UniqueConstraint("owner", "name", name="uq_templates_owner_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    owner: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Prompt content
    system: Mapped[str | None] = mapped_column(Text, nullable=True)
    messages: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Config overrides (lowest priority)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Declared variable slots — informational; missing vars still raise 422
    variables: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Template id={self.id} owner={self.owner!r} name={self.name!r}>"


class UsageEvent(Base):
    """
    Immutable per-request usage record. Never updated — append only.

    Columns
    -------
    key_id            UUID of the ApiKey that made the request.
                      Intentionally NOT a FK — this is a high-volume
                      append-only table; FK constraint would add write
                      overhead and complicate key hard-deletes.
    request_id        Propagated from X-Request-Id header.
    model             Actual model returned by upstream (may differ from
                      requested if OpenRouter fell back to an alternative).
    template_id       UUID of the Template used, if any.
    stream            Whether this was a streaming request.
    prompt_tokens     Input tokens charged. NULL if upstream didn't report.
    completion_tokens Output tokens charged. NULL if upstream didn't report.
    total_tokens      Sum of prompt + completion tokens.
    cost_usd          Calculated from static pricing table. NULL for
                      unknown models. Phase 7 replaces with live pricing.
    latency_ms        Wall-clock ms from request start to last byte.
    status            "success" | "error"
    error_code        RouterV error_code if status == "error".
    """

    __tablename__ = "usage_events"
    __table_args__ = (
        # Composite index: per-key time-range queries (most common access pattern)
        Index("ix_usage_events_key_created", "key_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    stream: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<UsageEvent id={self.id} key_id={self.key_id} "
            f"model={self.model!r} status={self.status!r}>"
        )


class ProviderKey(Base):
    """
    Per-owner upstream API key record.

    The actual key value lives in GCP Secret Manager; this row holds only
    the resource path (secret_ref) plus metadata.  At request time the
    resolver fetches the secret, caches it in Redis for ~5 minutes, and
    passes it to the upstream adapter.

    Columns
    -------
    owner        Matches api_key.owner — provider keys are owner-scoped.
    provider     Upstream provider slug: "openrouter", "openai", etc.
                 Only "openrouter" is used in the current adapter set.
    secret_ref   GCP Secret Manager resource name, e.g.:
                   projects/<project>/secrets/<secret-name>/versions/latest
                 In local dev this field may be empty — the resolver falls
                 back to settings.openrouter_api_key in that case.
    label        Human note: "acme prod", "bob personal", etc.
    is_active    False = soft-deleted / being rotated.  The resolver only
                 selects active rows.
    """

    __tablename__ = "provider_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    owner: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    secret_ref: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ProviderKey id={self.id} owner={self.owner!r} "
            f"provider={self.provider!r} active={self.is_active}>"
        )
