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
    name: Mapped[str] = mapped_column(Text, nullable=False)  # covered by uq_templates_owner_name
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
    cost_usd          What we charged the user (USD), calculated from our
                      model_prices table. NULL when token counts unavailable.
    upstream_cost_usd Raw USD amount reported by OpenRouter in usage.cost.
                      Reference only — not used for billing, kept for margin
                      reconciliation (our cost vs what we charged). NULL when
                      upstream omits the field.
    cached_tokens     Prompt tokens served from provider cache. NULL if not reported.
    latency_ms        Wall-clock ms from request start to last byte.
    status            "success" | "error"
    error_code        RouterV error_code if status == "error".
    """

    __tablename__ = "usage_events"
    __table_args__ = (
        # Composite index: per-key time-range queries (most common access pattern)
        Index("ix_usage_events_key_created", "key_id", "created_at"),
        Index("ix_usage_events_provider", "provider"),
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
    # Raw upstream cost from OpenRouter usage.cost — reference only, not used for billing.
    upstream_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    # Phase 6 — populated from usage.prompt_tokens_details.cached_tokens in
    # the upstream response.  NULL = provider did not report cache data.
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Provider that handled this request — matches model_prices.provider.
    # Populated from resolve_provider() in the inference router.
    provider: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="openrouter"
    )
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
    # OpenRouter Management API hash — returned when the key was auto-provisioned.
    # Used for disable / delete / rotate calls.  NULL for manually registered keys.
    or_key_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class UserBalance(Base):
    """
    Account-level credit balance for a RouterV user.

    One row per user (upserted on payment). Balance is decremented after
    each paid inference request and incremented on payment.

    Columns
    -------
    user_id      Supabase user UUID (sub claim). Matches ApiKey.owner when
                 SUPABASE_OWNER_CLAIM is unset.
    balance_usd  Current credit balance in USD. Can go slightly negative
                 due to post-deduction model (last request overshoots).
    """

    __tablename__ = "user_balances"

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    balance_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, server_default="0"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UserBalance user_id={self.user_id!r} balance={self.balance_usd}>"


class Model(Base):
    """
    Admin-managed model registry — the canonical whitelist for GET /v1/models.

    Only models with a row here are returned by the public models API.
    model_prices owns pricing and provider routing independently; the two
    tables are joined at query time (model_prices.is_default=true row provides
    the pricing shown to users).

    Columns
    -------
    model_id        Exact model identifier, e.g. "openai/gpt-4o-mini".
                    Must match the model_id used in model_prices rows.
    name            Human-readable display name, e.g. "GPT-4o Mini".
    context_length  Max context window in tokens. NULL if unknown.
    description     Optional marketing/capability description.
    is_enabled      False = hidden from the public listing (soft disable).
                    Pricing and routing still function for keys that already
                    use this model; only the discovery API filters it out.
    """

    __tablename__ = "models"

    model_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    context_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", index=True
    )
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
        return (
            f"<Model model_id={self.model_id!r} name={self.name!r} "
            f"enabled={self.is_enabled}>"
        )


class ModelPrice(Base):
    """
    Admin-managed pricing for each model, keyed by (model_id, provider).

    Columns
    -------
    model_id               Exact model identifier, e.g. "openai/gpt-4o-mini".
    provider               Upstream provider slug: "openrouter", "vertex",
                           "bedrock", "openai". Part of composite primary key.
    provider_model_id      The exact model ID the upstream provider expects,
                           e.g. "us.anthropic.claude-3-haiku-20240307-v1:0".
                           NULL = not set; adapters fall back to their internal
                           _MODEL_MAP translation in that case.
    is_default             True for the provider that handles this model when
                           no explicit provider preference is given. At most one
                           row per model_id may have is_default=True (enforced
                           by the partial unique index ix_model_prices_one_default).
    prompt_usd_per_1k      Our charge per 1 000 prompt tokens.
    completion_usd_per_1k  Our charge per 1 000 completion tokens.
    is_free                When True, requests are never billed regardless of
                           token counts. Used for free-tier models.
    """

    __tablename__ = "model_prices"

    model_id: Mapped[str] = mapped_column(Text, primary_key=True)
    provider: Mapped[str] = mapped_column(
        Text, primary_key=True, server_default="openrouter"
    )
    provider_model_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    prompt_usd_per_1k: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False)
    completion_usd_per_1k: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False)
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # What the upstream provider charges us per 1 000 tokens.
    # NULL = not configured; logger cannot calculate upstream_cost_usd for this row.
    upstream_prompt_usd_per_1k: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    upstream_completion_usd_per_1k: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ModelPrice model_id={self.model_id!r} provider={self.provider!r} "
            f"default={self.is_default} prompt={self.prompt_usd_per_1k} free={self.is_free}>"
        )


class CurrencyConversionRate(Base):
    """
    Append-only log of FX rate snapshots fetched by the scheduler.

    Each call to POST /v1/fx-rates/refresh inserts a new row; rows are never
    updated in place.  Readers always query the latest row for a given currency
    (ORDER BY created_at DESC LIMIT 1).

    Columns
    -------
    id          UUID primary key.
    currency    ISO 4217 currency code (e.g. "INR", "EUR"). Indexed, not unique.
    rate        Raw units of this currency per 1 USD as returned by the exchange
                rate API (e.g. INR: 93.8571).
    markup_fee  0.2 % of rate — the absolute markup added on top of the raw rate.
    total_rate  rate + markup_fee — the effective rate used when converting
                payment amounts to USD (divide INR amount by total_rate).
    created_at  Timestamp of this snapshot. Used to resolve the latest rate.
    """

    __tablename__ = "currency_conversion_rates"
    __table_args__ = (
        Index("ix_currency_conversion_rates_currency_created", "currency", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    currency: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    # 0.2 % markup expressed as an absolute amount (rate * 0.002)
    markup_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    # rate + markup_fee — the effective rate charged to callers
    total_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CurrencyConversionRate currency={self.currency!r} rate={self.rate}>"


class PaymentEvent(Base):
    """
    Append-only log of inbound payment webhook events.

    Columns
    -------
    user_id          External user identifier from the payment provider.
    payment_id       Unique payment / transaction identifier.
    provider         Payment provider slug: "stripe", "paddle", etc.
    order_id         Provider-side order / invoice identifier.
    currency         ISO 4217 currency code (e.g. "USD", "EUR").
    amount           Charged amount in the smallest currency unit (e.g. cents).
    metadata         Arbitrary provider-specific data (e.g. cashfree_importer_details_submitted).
    """

    __tablename__ = "payment_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    payment_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    order_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<PaymentEvent id={self.id} user_id={self.user_id!r} "
            f"payment_id={self.payment_id!r} provider={self.provider!r}>"
        )


class Discount(Base):
    """
    Per-user discount applied before balance deduction.

    Columns
    -------
    user_id       Matches ApiKey.owner — discount is owner-scoped.
    model_id      NULL = account-level (all models).
                  Set = model-level (this model only).
                  Model-level takes priority over account-level (non-stackable).
    discount_pct  Percentage reduction: 0.00–100.00.
    valid_from    Discount becomes active at this timestamp.
    valid_until   Discount expires at this timestamp. NULL = no expiry.
    is_active     False = manually deactivated by admin.
    label         Admin note e.g. "Q2 promo", "partner deal".
    """

    __tablename__ = "discounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    model_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        scope = f"model={self.model_id!r}" if self.model_id else "account-level"
        return f"<Discount id={self.id} user={self.user_id!r} {scope} pct={self.discount_pct}>"
