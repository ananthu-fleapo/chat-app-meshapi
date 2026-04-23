-- =============================================================================
-- model_pricing — full schema
-- PostgreSQL 14+
-- =============================================================================

-- -----------------------------------------------------------------------------
-- ENUMS
-- -----------------------------------------------------------------------------

-- All supported pricing units across providers.
-- per_1k_tokens / per_1m_tokens : most LLM text models
-- per_1k_chars                  : character-based billing (some Asian providers)
-- per_image                     : image generation (DALL-E, Imagen, Stable Diffusion)
-- per_second / per_minute       : audio / transcription models (Whisper, Voxtral)
-- per_request                   : flat fee per API call regardless of tokens
-- per_session                   : stateful session billing (Realtime API)
-- per_call                      : tool / feature invocations (web search, code interpreter)
CREATE TYPE pricing_unit_enum AS ENUM (
    'per_1k_tokens',
    'per_1m_tokens',
    'per_1k_chars',
    'per_image',
    'per_second',
    'per_minute',
    'per_request',
    'per_session',
    'per_call'
);

-- Supported input/output modality types.
-- A single model can belong to multiple (e.g. ['text','image'] for vision models).
CREATE TYPE modality_enum AS ENUM (
    'text',
    'image',
    'audio',
    'video',
    'embedding',
    'transcription',
    'code'
);

-- Quality tiers used by image generation models (e.g. DALL-E 3 standard vs hd).
-- Referenced by the child table model_pricing_image_sizes.
CREATE TYPE image_quality_enum AS ENUM (
    'standard',
    'hd',
    'low',
    'medium',
    'high',
    'ultra'
);

-- Distinct token stream types for multimodal / realtime models.
-- Used by the child table model_pricing_token_types (e.g. OpenAI Realtime API).
CREATE TYPE token_type_enum AS ENUM (
    'text_input',
    'text_output',
    'audio_input',
    'audio_output',
    'cached_text_input',
    'cached_audio_input'
);


-- =============================================================================
-- PARENT TABLE
-- =============================================================================

CREATE TABLE model_pricing (

    -- -------------------------------------------------------------------------
    -- Identity
    -- Uniquely identifies a model as served by a specific provider.
    -- The same underlying model can appear multiple times — once per provider
    -- (e.g. anthropic/claude-sonnet-4-6 on both bedrock and openrouter).
    -- -------------------------------------------------------------------------

    -- Surrogate primary key. Used as the FK target in all child tables.
    id                                  BIGSERIAL               NOT NULL,

    -- Internal namespaced key: <org>/<model-slug>  e.g. openai/gpt-4o
    -- Combines with provider to form the deduplication key.
    model_id                            TEXT                    NOT NULL,

    -- The raw model string passed directly to the provider's API.
    -- e.g. gpt-4o, us.anthropic.claude-sonnet-4-6, gemini-2.5-pro
    -- Can differ significantly from model_id (Bedrock ARN-style IDs, etc.)
    provider_model_id                   TEXT                    NOT NULL,

    -- Human-readable display name. e.g. "GPT-4o", "Claude Sonnet 4.6"
    model_name                          TEXT                    NOT NULL,

    -- Provider slug. e.g. openai, anthropic, bedrock, vertex, openrouter, qwen
    provider                            TEXT                    NOT NULL,


    -- -------------------------------------------------------------------------
    -- Modality & capabilities
    -- Describes what the model can accept as input and produce as output,
    -- plus which API features it supports.
    -- -------------------------------------------------------------------------

    -- Full set of modalities the model works with.
    -- e.g. ARRAY['text','image']::modality_enum[] for a vision model.
    modality                            modality_enum[]         NOT NULL,

    -- Subset of modality[] that the model accepts as input.
    -- NULL means same as modality (no distinction needed).
    input_modalities                    modality_enum[]         NULL,

    -- Subset of modality[] that the model produces as output.
    -- NULL means same as modality (no distinction needed).
    output_modalities                   modality_enum[]         NULL,

    -- Whether the model supports function / tool calling.
    supports_tools                      BOOLEAN                 NOT NULL    DEFAULT FALSE,

    -- Whether the model supports JSON schema / structured output mode.
    supports_structured_output          BOOLEAN                 NOT NULL    DEFAULT FALSE,

    -- Whether the model accepts a system-role message in the prompt.
    supports_system_prompt              BOOLEAN                 NOT NULL    DEFAULT TRUE,

    -- Whether the model supports an extended thinking / reasoning mode
    -- where it produces a visible chain-of-thought before its final answer.
    -- e.g. o3, o4-mini, DeepSeek-R1, Claude 3.7 Sonnet :thinking
    supoorts_thinking                   BOOLEAN                 NOT NULL    DEFAULT FALSE,

    -- Whether the model is available via the provider's batch / async API
    -- (typically ~50 % cheaper, with higher latency SLAs).
    suports_batching                    BOOLEAN                 NOT NULL    DEFAULT FALSE,

    -- Whether the model is accessible via the standard completions API
    -- (POST /v1/chat/completions or equivalent).
    supports_completions_api            BOOLEAN                 NOT NULL    DEFAULT TRUE,

    -- Whether the model is accessible via the newer responses API
    -- (POST /v1/responses or equivalent — OpenAI, some qwen models).
    supports_responses_api              BOOLEAN                 NOT NULL    DEFAULT FALSE,

    -- Whether the model exposes an embeddings endpoint
    -- (POST /v1/embeddings or equivalent).
    supports_embeddings                 BOOLEAN                 NOT NULL    DEFAULT FALSE,


    -- -------------------------------------------------------------------------
    -- Pricing unit & base costs
    -- Core per-token (or per-unit) prices for standard inference.
    -- All costs are expressed in USD per one pricing_unit.
    -- -------------------------------------------------------------------------

    -- The billing unit that input_cost / output_cost are denominated in.
    -- e.g. 'per_1k_tokens' means the cost figures are price-per-1000-tokens.
    pricing_unit                        pricing_unit_enum       NOT NULL,

    -- ISO 4217 currency code. Almost always USD; stored for future-proofing.
    currency                            CHAR(3)                 NOT NULL    DEFAULT 'USD',

    -- Cost per pricing_unit for prompt / input tokens.
    -- NULL for output-only models (image generation, TTS).
    input_cost                          NUMERIC(20,10)          NULL,

    -- Cost per pricing_unit for completion / output tokens.
    -- NULL for input-only models (embeddings, transcription).
    output_cost                         NUMERIC(20,10)          NULL,

    -- Flat per-request charge applied in addition to token costs, if any.
    -- e.g. some search-augmented models charge a fixed fee per call.
    request_cost                        NUMERIC(20,10)          NULL,


    -- -------------------------------------------------------------------------
    -- Long-context pricing tiers
    -- Some providers (Google Gemini, etc.) switch to a higher rate once the
    -- prompt exceeds a token threshold. NULL = flat pricing, no tiers.
    -- -------------------------------------------------------------------------

    -- Maximum context length the model supports, in tokens.
    context_window                      INTEGER                 NULL,

    -- Token count below which standard (cheaper) rates apply.
    -- When prompt exceeds this value, the long_context_* rates kick in.
    -- NULL means no tiered pricing — input_cost / output_cost apply at all sizes.
    standard_context_threshold          INTEGER                 NULL,

    -- Input cost per pricing_unit when prompt exceeds standard_context_threshold.
    long_context_input_cost             NUMERIC(20,10)          NULL,

    -- Output cost per pricing_unit in long-context mode.
    long_context_output_cost            NUMERIC(20,10)          NULL,


    -- -------------------------------------------------------------------------
    -- Prompt caching — standard context
    -- Providers that support prompt caching charge a reduced rate for cache hits
    -- and sometimes a premium for writing tokens into the cache.
    -- NULL = caching not supported by this model / provider.
    -- -------------------------------------------------------------------------

    -- Cost per pricing_unit for a cache-hit read (standard context).
    -- Typically a fraction of input_cost  (e.g. Anthropic: 10 % of base).
    cache_read_input_cost               NUMERIC(20,10)          NULL,

    -- Cost per pricing_unit to write tokens into the prompt cache (standard context).
    -- Can be higher than input_cost  (e.g. Anthropic: 125 % of base).
    cache_write_input_cost              NUMERIC(20,10)          NULL,


    -- -------------------------------------------------------------------------
    -- Prompt caching — long context
    -- Same cache mechanics as above but applied when the prompt exceeds
    -- standard_context_threshold. Some providers have separate cache rates
    -- at long context (e.g. Gemini 1.5 Pro).
    -- NULL = no differentiated long-context cache pricing.
    -- -------------------------------------------------------------------------

    -- Cache-hit read cost per pricing_unit in long-context mode.
    long_context_cache_read_input_cost  NUMERIC(20,10)          NULL,

    -- Cache-write cost per pricing_unit in long-context mode.
    long_context_cache_write_input_cost NUMERIC(20,10)          NULL,


    -- -------------------------------------------------------------------------
    -- Batch & async pricing
    -- Discounted rates available when using the provider's batch / async API.
    -- NULL = batch API not available for this model.
    -- -------------------------------------------------------------------------

    -- Discounted input cost per pricing_unit in batch mode.
    batch_input_cost                    NUMERIC(20,10)          NULL,

    -- Discounted output cost per pricing_unit in batch mode.
    batch_output_cost                   NUMERIC(20,10)          NULL,


    -- -------------------------------------------------------------------------
    -- Fine-tuning
    -- Costs associated with training a custom checkpoint and then running it.
    -- NULL = fine-tuning not supported for this model.
    -- -------------------------------------------------------------------------

    -- Cost per pricing_unit to fine-tune this base model.
    training_cost                       NUMERIC(20,10)          NULL,

    -- Inference input cost when calling a fine-tuned checkpoint of this model.
    -- Typically higher than the base input_cost.
    fine_tuned_input_cost               NUMERIC(20,10)          NULL,

    -- Inference output cost for a fine-tuned checkpoint.
    fine_tuned_output_cost              NUMERIC(20,10)          NULL,


    -- -------------------------------------------------------------------------
    -- Modality-specific costs
    -- Per-unit costs for non-token modalities. Most fields are NULL for
    -- standard text models. For models with complex size/quality pricing
    -- (DALL-E 3, Imagen) use the child table model_pricing_image_sizes instead.
    -- -------------------------------------------------------------------------

    -- Cost per image submitted as input (vision / multimodal models).
    image_input_cost                    NUMERIC(20,10)          NULL,

    -- Cost per image generated (image-gen models). Represents the base/default
    -- resolution. Use model_pricing_image_sizes for per-size breakdowns.
    image_output_cost                   NUMERIC(20,10)          NULL,

    -- Resolution string at which image_output_cost applies. e.g. '1024x1024'
    -- NULL when cost is size-agnostic or when child table is used instead.
    image_output_size                   TEXT                    NULL,

    -- Cost per pricing_unit of audio submitted as input to a multimodal model
    -- (real-time audio, not transcription). e.g. GPT-4o audio input.
    audio_input_cost                    NUMERIC(20,10)          NULL,

    -- Cost per pricing_unit of audio generated as output (TTS / voice models).
    audio_output_cost                   NUMERIC(20,10)          NULL,

    -- Cost per pricing_unit (typically per_minute) of audio/video transcribed.
    -- Populated for dedicated transcription models like Whisper, Voxtral.
    -- NULL for all other model types.
    transcription_cost                  NUMERIC(20,10)          NULL,


    -- -------------------------------------------------------------------------
    -- Lifecycle & metadata
    -- -------------------------------------------------------------------------

    -- TRUE for the single preferred provider route for this model_id.
    -- Enforced by ix_model_pricing_one_default (partial unique index below):
    -- at most one row per model_id may have is_default = TRUE.
    is_default                          BOOLEAN                 NOT NULL    DEFAULT FALSE,

    -- FALSE once the model has been deprecated / retired by the provider.
    -- Retired rows are kept for historical cost lookups rather than deleted.
    is_active                           BOOLEAN                 NOT NULL    DEFAULT TRUE,

    -- Date from which this pricing row is valid.
    -- Together with (model_id, provider) this enables full price history:
    -- insert a new row when a provider changes prices instead of updating.
    effective_date                      DATE                    NOT NULL,

    -- Date the model was retired by the provider. NULL while still active.
    deprecated_date                     DATE                    NULL,

    -- Free-text notes: pricing quirks, regional restrictions, sentinel values,
    -- supported API flags not captured by boolean columns, etc.
    notes                               TEXT                    NULL,

    -- URL of the provider's pricing page at the time this row was written.
    -- Useful for audit trails and verifying prices manually.
    source_url                          TEXT                    NULL,

    -- Row creation timestamp. Set once on INSERT, never updated.
    created_at                          TIMESTAMPTZ             NOT NULL    DEFAULT now(),

    -- Last modification timestamp. Maintained automatically by trigger below.
    updated_at                          TIMESTAMPTZ             NOT NULL    DEFAULT now(),


    -- -------------------------------------------------------------------------
    -- Constraints
    -- -------------------------------------------------------------------------

    CONSTRAINT model_pricing_pkey
        PRIMARY KEY (id),

    -- One row per (model, provider) combination.
    -- The same model can exist on multiple providers (bedrock, vertex, openrouter)
    -- but each provider gets exactly one current row.
    CONSTRAINT model_pricing_model_id_provider_unique
        UNIQUE (model_id, provider),

    -- Enables price history: re-insert with a new effective_date when prices change.
    -- Never update costs in place — old rows stay for historical reporting.
    CONSTRAINT model_pricing_history_unique
        UNIQUE (model_id, provider, effective_date),

    -- Sanity-check: costs must be zero or positive (or NULL = not applicable).
    CONSTRAINT model_pricing_input_cost_nonneg
        CHECK (input_cost IS NULL OR input_cost >= 0),

    CONSTRAINT model_pricing_output_cost_nonneg
        CHECK (output_cost IS NULL OR output_cost >= 0),

    CONSTRAINT model_pricing_request_cost_nonneg
        CHECK (request_cost IS NULL OR request_cost >= 0),

    -- Long-context tier columns are only meaningful when a threshold is defined.
    CONSTRAINT model_pricing_long_context_requires_threshold
        CHECK (
            (long_context_input_cost IS NULL AND long_context_output_cost IS NULL)
            OR standard_context_threshold IS NOT NULL
        ),

    -- Same guard for long-context cache columns.
    CONSTRAINT model_pricing_long_context_cache_requires_threshold
        CHECK (
            (long_context_cache_read_input_cost IS NULL AND long_context_cache_write_input_cost IS NULL)
            OR standard_context_threshold IS NOT NULL
        ),

    -- A model can only be deprecated after it became effective.
    CONSTRAINT model_pricing_deprecated_after_effective
        CHECK (deprecated_date IS NULL OR deprecated_date >= effective_date)
);


-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------

-- provider: used in every query that filters by a specific provider
-- (e.g. "give me all bedrock models", "compare openai vs vertex pricing").
CREATE INDEX idx_model_pricing_provider
    ON model_pricing (provider);

-- is_active: used to quickly exclude deprecated models from live pricing queries.
-- Partial index would be smaller but a full index is simpler to maintain.
CREATE INDEX idx_model_pricing_is_active
    ON model_pricing (is_active);

-- effective_date: used for point-in-time pricing queries
-- ("what did this model cost on 2025-01-01?") and range scans on price history.
CREATE INDEX idx_model_pricing_effective_date
    ON model_pricing (effective_date);

-- modality: GIN index on the array column enables efficient containment queries
-- e.g. WHERE modality @> ARRAY['image']::modality_enum[]
-- to find all vision or transcription models across providers.
CREATE INDEX idx_model_pricing_modality
    ON model_pricing USING GIN (modality);

-- is_default (partial unique): enforces the business rule that at most ONE row
-- per model_id can be the default provider route. Partial indexes only index
-- rows where the condition is TRUE, so this is both a uniqueness constraint
-- and an efficient lookup index for "give me the default row for this model".
CREATE UNIQUE INDEX ix_model_pricing_one_default
    ON model_pricing (model_id)
    WHERE (is_default = TRUE);


-- -----------------------------------------------------------------------------
-- Trigger: keep updated_at current on every UPDATE
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION model_pricing_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_model_pricing_updated_at
    BEFORE UPDATE ON model_pricing
    FOR EACH ROW EXECUTE FUNCTION model_pricing_set_updated_at();