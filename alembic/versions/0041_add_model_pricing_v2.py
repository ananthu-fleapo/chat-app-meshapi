"""add model_pricing v2 table with ENUMs

Revision ID: 0041
Revises: 0040
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUM types ────────────────────────────────────────────────────────────
    pricing_unit_enum = postgresql.ENUM(
        "per_1k_tokens",
        "per_1m_tokens",
        "per_1k_chars",
        "per_image",
        "per_second",
        "per_minute",
        "per_request",
        "per_session",
        "per_call",
        name="pricing_unit_enum",
        create_type=True,
    )
    modality_enum = postgresql.ENUM(
        "text",
        "image",
        "audio",
        "video",
        "embedding",
        "transcription",
        "code",
        name="modality_enum",
        create_type=True,
    )
    image_quality_enum = postgresql.ENUM(
        "standard",
        "hd",
        "low",
        "medium",
        "high",
        "ultra",
        name="image_quality_enum",
        create_type=True,
    )
    token_type_enum = postgresql.ENUM(
        "text_input",
        "text_output",
        "audio_input",
        "audio_output",
        "cached_text_input",
        "cached_audio_input",
        name="token_type_enum",
        create_type=True,
    )
    pricing_unit_enum.create(op.get_bind(), checkfirst=True)
    modality_enum.create(op.get_bind(), checkfirst=True)
    image_quality_enum.create(op.get_bind(), checkfirst=True)
    token_type_enum.create(op.get_bind(), checkfirst=True)

    # ── model_pricing table ───────────────────────────────────────────────────
    op.create_table(
        "model_pricing",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # Identity
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("provider_model_id", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        # Modality & capabilities
        sa.Column("modality", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("input_modalities", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("output_modalities", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("supports_tools", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("supports_structured_output", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("supports_system_prompt", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("supports_thinking", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("supports_batching", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("supports_completions_api", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("supports_responses_api", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("supports_embeddings", sa.Boolean(), nullable=False, server_default="false"),
        # Pricing unit & base costs
        sa.Column("pricing_unit", sa.Text(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("input_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("output_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("request_cost", sa.Numeric(20, 10), nullable=True),
        # Long-context tiers
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("standard_context_threshold", sa.Integer(), nullable=True),
        sa.Column("long_context_input_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("long_context_output_cost", sa.Numeric(20, 10), nullable=True),
        # Prompt caching — standard context
        sa.Column("cache_read_input_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("cache_write_input_cost", sa.Numeric(20, 10), nullable=True),
        # Prompt caching — long context
        sa.Column("long_context_cache_read_input_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("long_context_cache_write_input_cost", sa.Numeric(20, 10), nullable=True),
        # Batch pricing
        sa.Column("batch_input_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("batch_output_cost", sa.Numeric(20, 10), nullable=True),
        # Fine-tuning
        sa.Column("training_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("fine_tuned_input_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("fine_tuned_output_cost", sa.Numeric(20, 10), nullable=True),
        # Modality-specific costs
        sa.Column("image_input_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("image_output_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("image_output_size", sa.Text(), nullable=True),
        sa.Column("audio_input_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("audio_output_cost", sa.Numeric(20, 10), nullable=True),
        sa.Column("transcription_cost", sa.Numeric(20, 10), nullable=True),
        # Lifecycle
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_free", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("deprecated_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="model_pricing_pkey"),
        sa.UniqueConstraint("model_id", "provider", name="model_pricing_model_id_provider_unique"),
        sa.UniqueConstraint("model_id", "provider", "effective_date", name="model_pricing_history_unique"),
        sa.CheckConstraint("input_cost IS NULL OR input_cost >= 0", name="model_pricing_input_cost_nonneg"),
        sa.CheckConstraint("output_cost IS NULL OR output_cost >= 0", name="model_pricing_output_cost_nonneg"),
        sa.CheckConstraint("request_cost IS NULL OR request_cost >= 0", name="model_pricing_request_cost_nonneg"),
        sa.CheckConstraint(
            "(long_context_input_cost IS NULL AND long_context_output_cost IS NULL) OR standard_context_threshold IS NOT NULL",
            name="model_pricing_long_context_requires_threshold",
        ),
        sa.CheckConstraint(
            "(long_context_cache_read_input_cost IS NULL AND long_context_cache_write_input_cost IS NULL) OR standard_context_threshold IS NOT NULL",
            name="model_pricing_long_context_cache_requires_threshold",
        ),
        sa.CheckConstraint(
            "deprecated_date IS NULL OR deprecated_date >= effective_date",
            name="model_pricing_deprecated_after_effective",
        ),
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    op.create_index("idx_model_pricing_provider", "model_pricing", ["provider"])
    op.create_index("idx_model_pricing_is_active", "model_pricing", ["is_active"])
    op.create_index("idx_model_pricing_effective_date", "model_pricing", ["effective_date"])
    op.create_index(
        "idx_model_pricing_modality",
        "model_pricing",
        ["modality"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_model_pricing_one_default",
        "model_pricing",
        ["model_id"],
        unique=True,
        postgresql_where="is_default = TRUE",
    )

    # ── updated_at trigger ────────────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION model_pricing_set_updated_at()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_model_pricing_updated_at
            BEFORE UPDATE ON model_pricing
            FOR EACH ROW EXECUTE FUNCTION model_pricing_set_updated_at();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_model_pricing_updated_at ON model_pricing;")
    op.execute("DROP FUNCTION IF EXISTS model_pricing_set_updated_at();")
    op.drop_table("model_pricing")
    op.execute("DROP TYPE IF EXISTS token_type_enum;")
    op.execute("DROP TYPE IF EXISTS image_quality_enum;")
    op.execute("DROP TYPE IF EXISTS modality_enum;")
    op.execute("DROP TYPE IF EXISTS pricing_unit_enum;")
