-- ================================================================
-- model_pricing — generated INSERT statements
-- Source rows   : 387
-- After dedup   : 387  (unique model_id + provider)
-- Generated     : 2026-04-23 12:47 UTC
-- Strategy      : ON CONFLICT (model_id, provider, effective_date)
--                 DO UPDATE to refresh costs + notes
-- ================================================================

BEGIN;

-- ai21/jamba-1-5-large-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'ai21/jamba-1-5-large-v1', 'ai21.jamba-1-5-large-v1:0', 'jamba 1 5 large v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.008,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- ai21/jamba-1-5-mini-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'ai21/jamba-1-5-mini-v1', 'ai21.jamba-1-5-mini-v1:0', 'jamba 1 5 mini v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- amazon/nova-2-lite-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'amazon/nova-2-lite-v1', 'us.amazon.nova-2-lite-v1:0', 'Nova 2 lite v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    6e-05, 0.00024,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- amazon/nova-lite-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'amazon/nova-lite-v1', 'amazon.nova-lite-v1:0', 'Nova lite v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    6e-05, 0.00024,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- amazon/nova-micro-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'amazon/nova-micro-v1', 'amazon.nova-micro-v1:0', 'Nova micro v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    4e-05, 0.00014,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- amazon/nova-pro-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'amazon/nova-pro-v1', 'amazon.nova-pro-v1:0', 'Nova pro v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0008, 0.0032,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-3-haiku  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-3-haiku', 'anthropic.claude-3-haiku-20240307-v1:0', 'Claude 3 haiku', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00025, 0.00125,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-haiku-4.5  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-haiku-4.5', 'us.anthropic.claude-haiku-4-5-20251001-v1:0', 'Claude haiku 4.5', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0008, 0.004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-opus-4.1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-opus-4.1', 'us.anthropic.claude-opus-4-1-20250805-v1:0', 'Claude opus 4.1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.015, 0.075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-opus-4.5  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-opus-4.5', 'us.anthropic.claude-opus-4-5-20251101-v1:0', 'Claude opus 4.5', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.015, 0.075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-opus-4.6  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-opus-4.6', 'us.anthropic.claude-opus-4-6-v1', 'Claude opus 4.6', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.015, 0.075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-opus-4.7  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-opus-4.7', 'us.anthropic.claude-opus-4-7', 'Claude opus 4.7', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.005, 0.025,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-16', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-sonnet-4  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-sonnet-4', 'us.anthropic.claude-sonnet-4-20250514-v1:0', 'Claude sonnet 4', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-sonnet-4-6  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-sonnet-4-6', 'us.anthropic.claude-sonnet-4-6', 'Claude sonnet 4 6', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-sonnet-4.5  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-sonnet-4.5', 'us.anthropic.claude-sonnet-4-5-20250929-v1:0', 'Claude sonnet 4.5', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- deepseek/deepseek-r1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'deepseek/deepseek-r1', 'us.deepseek.r1-v1:0', 'DeepSeek r1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00135, 0.0054,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- deepseek/deepseek-v3.2  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'deepseek/deepseek-v3.2', 'deepseek.v3.2', 'DeepSeek v3.2', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00062, 0.00185,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemma-3-12b-it  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemma-3-12b-it', 'google.gemma-3-12b-it', 'Gemma 3 12b it', 'bedrock',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    9e-05, 0.00029,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemma-3-4b-it  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemma-3-4b-it', 'google.gemma-3-4b-it', 'Gemma 3 4b it', 'bedrock',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    4e-05, 8e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3-70b-instruct  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3-70b-instruct', 'meta.llama3-70b-instruct-v1:0', 'Llama 3 70b instruct', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00072, 0.00072,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3-8b-instruct  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3-8b-instruct', 'meta.llama3-8b-instruct-v1:0', 'Llama 3 8b instruct', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3.1-70b-instruct  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3.1-70b-instruct', 'us.meta.llama3-1-70b-instruct-v1:0', 'Llama 3.1 70b instruct', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00072, 0.00072,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3.1-8b-instruct  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3.1-8b-instruct', 'us.meta.llama3-1-8b-instruct-v1:0', 'Llama 3.1 8b instruct', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3.3-70b-instruct  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3.3-70b-instruct', 'us.meta.llama3-3-70b-instruct-v1:0', 'Llama 3.3 70b instruct', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00072, 0.00072,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-4-maverick  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-4-maverick', 'us.meta.llama4-maverick-17b-instruct-v1:0', 'Llama 4 maverick', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00024, 0.00097,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-4-scout  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-4-scout', 'us.meta.llama4-scout-17b-instruct-v1:0', 'Llama 4 scout', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00017, 0.00017,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- minimax/minimax-m2  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'minimax/minimax-m2', 'minimax.minimax-m2', 'minimax m2', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0012,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- minimax/minimax-m2-1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'minimax/minimax-m2-1', 'minimax.minimax-m2.1', 'minimax m2 1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0012,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- minimax/minimax-m2-5  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'minimax/minimax-m2-5', 'minimax.minimax-m2.5', 'minimax m2 5', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0012,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistral/devstral-2-123b  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistral/devstral-2-123b', 'mistral.devstral-2-123b', 'devstral 2 123b', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0004, 0.002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistral/magistral-small-2509  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistral/magistral-small-2509', 'mistral.magistral-small-2509', 'Magistral small 2509', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0005, 0.0015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistral/ministral-3-14b-instruct  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistral/ministral-3-14b-instruct', 'mistral.ministral-3-14b-instruct', 'Ministral 3 14b instruct', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistral/ministral-3-3b-instruct  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistral/ministral-3-3b-instruct', 'mistral.ministral-3-3b-instruct', 'Ministral 3 3b instruct', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0001,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistral/ministral-3-8b-instruct  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistral/ministral-3-8b-instruct', 'mistral.ministral-3-8b-instruct', 'Ministral 3 8b instruct', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.00015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistral/mistral-7b-instruct-v0  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistral/mistral-7b-instruct-v0', 'mistral.mistral-7b-instruct-v0:2', 'Mistral 7b instruct v0', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.0002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistral/mistral-large-2402-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistral/mistral-large-2402-v1', 'mistral.mistral-large-2402-v1:0', 'Mistral large 2402 v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.004, 0.012,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistral/mistral-large-3-675b-instruct  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistral/mistral-large-3-675b-instruct', 'mistral.mistral-large-3-675b-instruct', 'Mistral large 3 675b instruct', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0005, 0.0015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistral/mistral-small-2402-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistral/mistral-small-2402-v1', 'mistral.mistral-small-2402-v1:0', 'Mistral small 2402 v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.001, 0.003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistral/pixtral-large-2502-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistral/pixtral-large-2502-v1', 'us.mistral.pixtral-large-2502-v1:0', 'pixtral large 2502 v1', 'bedrock',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistral/voxtral-mini-3b-2507  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistral/voxtral-mini-3b-2507', 'mistral.voxtral-mini-3b-2507', 'voxtral mini 3b 2507', 'bedrock',
    ARRAY['text','audio']::modality_enum[], ARRAY['text','audio']::modality_enum[], ARRAY['text','audio']::modality_enum[],
    'per_1k_tokens', 'USD',
    4e-05, 4e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mixtral-8x7b-instruct  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mixtral-8x7b-instruct', 'mistral.mixtral-8x7b-instruct-v0:1', 'Mixtral 8x7b instruct', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00045, 0.0007,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/voxtral-small-24b-2507  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/voxtral-small-24b-2507', 'mistral.voxtral-small-24b-2507', 'voxtral small 24b 2507', 'bedrock',
    ARRAY['text','audio']::modality_enum[], ARRAY['text','audio']::modality_enum[], ARRAY['text','audio']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- moonshotai/kimi-k2-thinking  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'moonshotai/kimi-k2-thinking', 'moonshot.kimi-k2-thinking', 'kimi k2 thinking', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0006, 0.0025,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- moonshotai/kimi-k2.5  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'moonshotai/kimi-k2.5', 'moonshotai.kimi-k2.5', 'kimi k2.5', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0006, 0.003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- nvidia/nemotron-3-nano-30b-a3b  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'nvidia/nemotron-3-nano-30b-a3b', 'nvidia.nemotron-nano-3-30b', 'nemotron 3 nano 30b a3b', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    6e-05, 0.00024,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-oss-120b  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-oss-120b', 'openai.gpt-oss-120b-1:0', 'GPT oss 120b', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API; responses_provider_model_id=openai.gpt-oss-120b'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-oss-safeguard-20b  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-oss-safeguard-20b', 'openai.gpt-oss-20b-1:0', 'GPT oss safeguard 20b', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    9e-05, 0.00039,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API; responses_provider_model_id=openai.gpt-oss-20b'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-32b-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-32b-v1', 'qwen.qwen3-32b-v1:0', 'Qwen3 32b v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-30b-a3b-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-30b-a3b-v1', 'qwen.qwen3-coder-30b-a3b-v1:0', 'Qwen3 coder 30b a3b v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.00062,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-next-80b-a3b  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-next-80b-a3b', 'qwen.qwen3-next-80b-a3b', 'Qwen3 next 80b a3b', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.0012,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- writer/palmyra-x4-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'writer/palmyra-x4-v1', 'us.writer.palmyra-x4-v1:0', 'palmyra x4 v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.005, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- writer/palmyra-x5-v1  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'writer/palmyra-x5-v1', 'us.writer.palmyra-x5-v1:0', 'palmyra x5 v1', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.006, 0.03,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- zai/glm-4-7  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'zai/glm-4-7', 'zai.glm-4.7', 'glm 4 7', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0006, 0.0022,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- zai/glm-4-7-flash  [bedrock]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'zai/glm-4-7-flash', 'zai.glm-4.7-flash', 'glm 4 7 flash', 'bedrock',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7e-05, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-3.5-turbo  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-3.5-turbo', 'gpt-3.5-turbo', 'GPT 3.5 turbo', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0005, 0.0015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-3.5-turbo-0125  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-3.5-turbo-0125', 'gpt-3.5-turbo-0125', 'GPT 3.5 turbo 0125', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0005, 0.0015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-3.5-turbo-1106  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-3.5-turbo-1106', 'gpt-3.5-turbo-1106', 'GPT 3.5 turbo 1106', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.001, 0.002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4-0613  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4-0613', 'gpt-4-0613', 'GPT 4 0613', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.03, 0.06,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4-turbo-2024-04-09  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4-turbo-2024-04-09', 'gpt-4-turbo-2024-04-09', 'GPT 4 turbo 2024 04 09', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.01, 0.03,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4.1  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4.1', 'gpt-4.1', 'GPT 4.1', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.008,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4.1-mini  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4.1-mini', 'gpt-4.1-mini', 'GPT 4.1 mini', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0004, 0.0016,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4.1-nano  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4.1-nano', 'gpt-4.1-nano', 'GPT 4.1 nano', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4o  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4o', 'gpt-4o', 'GPT 4o', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0025, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4o-2024-05-13  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4o-2024-05-13', 'gpt-4o-2024-05-13', 'GPT 4o 2024 05 13', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.005, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4o-mini  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4o-mini', 'gpt-4o-mini', 'GPT 4o mini', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5-nano  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5-nano', 'gpt-5-nano', 'GPT 5 nano', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    5e-05, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5-pro  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5-pro', 'gpt-5-pro', 'GPT 5 pro', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.015, 0.12,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    FALSE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'responses API only; responses_provider_model_id=gpt-5-pro'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.1  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.1', 'gpt-5.1', 'GPT 5.1', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00125, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.2  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.2', 'gpt-5.2', 'GPT 5.2', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00175, 0.014,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.4  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.4', 'gpt-5.4', 'GPT 5.4', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0025, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.4-mini  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.4-mini', 'gpt-5.4-mini', 'GPT 5.4 mini', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00075, 0.0045,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.4-nano  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.4-nano', 'gpt-5.4-nano', 'GPT 5.4 nano', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.00125,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/o1  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/o1', 'o1', 'O1', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.015, 0.06,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'supports thinking/reasoning mode; completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/o1-pro  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/o1-pro', 'o1-pro', 'O1 pro', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.15, 0.6,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    FALSE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'supports thinking/reasoning mode; responses API only; responses_provider_model_id=o1-pro'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/o3  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/o3', 'o3', 'O3', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.008,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/o3-mini  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/o3-mini', 'o3-mini', 'O3 mini', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0011, 0.0044,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/o4-mini  [openai]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/o4-mini', 'o4-mini', 'O4 mini', 'openai',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0011, 0.0044,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-14', 'supports thinking/reasoning mode; completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- ai21/jamba-large-1.7  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'ai21/jamba-large-1.7', 'jamba-large-1.7', 'jamba large 1.7', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.008,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- aion-labs/aion-1.0  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'aion-labs/aion-1.0', 'aion-1.0', 'aion 1.0', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.004, 0.008,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- aion-labs/aion-1.0-mini  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'aion-labs/aion-1.0-mini', 'aion-1.0-mini', 'aion 1.0 mini', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0007, 0.0014,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- aion-labs/aion-2.0  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'aion-labs/aion-2.0', 'aion-2.0', 'aion 2.0', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0008, 0.0016,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- aion-labs/aion-rp-llama-3.1-8b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'aion-labs/aion-rp-llama-3.1-8b', 'aion-rp-llama-3.1-8b', 'aion rp llama 3.1 8b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0008, 0.0016,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- alfredpros/codellama-7b-instruct-solidity  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'alfredpros/codellama-7b-instruct-solidity', 'codellama-7b-instruct-solidity', 'codellama 7b instruct solidity', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0008, 0.0012,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- allenai/olmo-3.1-32b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'allenai/olmo-3.1-32b-instruct', 'olmo-3.1-32b-instruct', 'olmo 3.1 32b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- alpindale/goliath-120b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'alpindale/goliath-120b', 'goliath-120b', 'goliath 120b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00375, 0.0075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- amazon/nova-2-lite-v1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'amazon/nova-2-lite-v1', 'nova-2-lite-v1', 'Nova 2 lite v1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0025,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- amazon/nova-lite-v1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'amazon/nova-lite-v1', 'nova-lite-v1', 'Nova lite v1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    6e-05, 0.00024,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- amazon/nova-micro-v1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'amazon/nova-micro-v1', 'nova-micro-v1', 'Nova micro v1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    3.5e-05, 0.00014,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- amazon/nova-premier-v1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'amazon/nova-premier-v1', 'nova-premier-v1', 'Nova premier v1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0025, 0.0125,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- amazon/nova-pro-v1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'amazon/nova-pro-v1', 'nova-pro-v1', 'Nova pro v1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0008, 0.0032,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthracite-org/magnum-v4-72b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthracite-org/magnum-v4-72b', 'magnum-v4-72b', 'magnum v4 72b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.005,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-3-haiku  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-3-haiku', 'claude-3-haiku', 'Claude 3 haiku', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00025, 0.00125,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-3.5-haiku  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-3.5-haiku', 'claude-3.5-haiku', 'Claude 3.5 haiku', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0008, 0.004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-3.7-sonnet  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-3.7-sonnet', 'claude-3.7-sonnet', 'Claude 3.7 sonnet', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-3.7-sonnet:thinking  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-3.7-sonnet:thinking', 'claude-3.7-sonnet', 'Claude 3.7 sonnet', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-haiku-4.5  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-haiku-4.5', 'claude-haiku-4.5', 'Claude haiku 4.5', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.001, 0.005,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-03', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-opus-4  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-opus-4', 'claude-opus-4', 'Claude opus 4', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.015, 0.075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-opus-4.1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-opus-4.1', 'claude-opus-4.1', 'Claude opus 4.1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.015, 0.075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-opus-4.5  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-opus-4.5', 'claude-opus-4.5', 'Claude opus 4.5', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.005, 0.025,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-03', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-opus-4.6  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-opus-4.6', 'claude-opus-4.6', 'Claude opus 4.6', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.005, 0.025,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-03', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-opus-4.7  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-opus-4.7', 'anthropic/claude-opus-4.7', 'Claude opus 4.7', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.005, 0.025,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-16', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-sonnet-4  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-sonnet-4', 'claude-sonnet-4', 'Claude sonnet 4', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-sonnet-4.5  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-sonnet-4.5', 'claude-sonnet-4.5', 'Claude sonnet 4.5', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-03', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- anthropic/claude-sonnet-4.6  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'anthropic/claude-sonnet-4.6', 'claude-sonnet-4.6', 'Claude sonnet 4.6', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- baidu/ernie-4.5-21b-a3b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'baidu/ernie-4.5-21b-a3b', 'ernie-4.5-21b-a3b', 'ernie 4.5 21b a3b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7e-05, 0.00028,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- baidu/ernie-4.5-300b-a47b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'baidu/ernie-4.5-300b-a47b', 'ernie-4.5-300b-a47b', 'ernie 4.5 300b a47b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00028, 0.0011,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- baidu/ernie-4.5-vl-28b-a3b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'baidu/ernie-4.5-vl-28b-a3b', 'ernie-4.5-vl-28b-a3b', 'ernie 4.5 vl 28b a3b', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00014, 0.00056,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- baidu/ernie-4.5-vl-424b-a47b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'baidu/ernie-4.5-vl-424b-a47b', 'ernie-4.5-vl-424b-a47b', 'ernie 4.5 vl 424b a47b', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00042, 0.00125,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- bytedance-seed/seed-1.6  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'bytedance-seed/seed-1.6', 'seed-1.6', 'seed 1.6', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00025, 0.002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- bytedance-seed/seed-1.6-flash  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'bytedance-seed/seed-1.6-flash', 'seed-1.6-flash', 'seed 1.6 flash', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7.5e-05, 0.0003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- bytedance-seed/seed-2.0-lite  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'bytedance-seed/seed-2.0-lite', 'seed-2.0-lite', 'seed 2.0 lite', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00025, 0.002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- bytedance-seed/seed-2.0-mini  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'bytedance-seed/seed-2.0-mini', 'seed-2.0-mini', 'seed 2.0 mini', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- bytedance/ui-tars-1.5-7b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'bytedance/ui-tars-1.5-7b', 'ui-tars-1.5-7b', 'ui tars 1.5 7b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- cohere/command-a  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'cohere/command-a', 'command-a', 'command a', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0025, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- cohere/command-r-08-2024  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'cohere/command-r-08-2024', 'command-r-08-2024', 'command r 08 2024', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- cohere/command-r-plus-08-2024  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'cohere/command-r-plus-08-2024', 'command-r-plus-08-2024', 'command r plus 08 2024', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0025, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- cohere/command-r7b-12-2024  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'cohere/command-r7b-12-2024', 'command-r7b-12-2024', 'command r7b 12 2024', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    3.75e-05, 0.00015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- deepcogito/cogito-v2.1-671b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'deepcogito/cogito-v2.1-671b', 'cogito-v2.1-671b', 'cogito v2.1 671b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00125, 0.00125,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- deepseek/deepseek-chat-v3-0324  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'deepseek/deepseek-chat-v3-0324', 'deepseek-chat-v3-0324', 'DeepSeek chat v3 0324', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.00077,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- deepseek/deepseek-chat-v3.1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'deepseek/deepseek-chat-v3.1', 'deepseek-chat-v3.1', 'DeepSeek chat v3.1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.00075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- deepseek/deepseek-r1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'deepseek/deepseek-r1', 'deepseek-r1', 'DeepSeek r1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0007, 0.0025,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route; supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- deepseek/deepseek-v3.1-terminus  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'deepseek/deepseek-v3.1-terminus', 'deepseek-v3.1-terminus', 'DeepSeek v3.1 terminus', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00021, 0.00079,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- deepseek/deepseek-v3.2  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'deepseek/deepseek-v3.2', 'deepseek-v3.2', 'DeepSeek v3.2', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00026, 0.00038,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-03', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- deepseek/deepseek-v3.2-exp  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'deepseek/deepseek-v3.2-exp', 'deepseek-v3.2-exp', 'DeepSeek v3.2 exp', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00027, 0.00041,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- essentialai/rnj-1-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'essentialai/rnj-1-instruct', 'rnj-1-instruct', 'rnj 1 instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.00015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.0-flash-001  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.0-flash-001', 'gemini-2.0-flash-001', 'Gemini 2.0 flash 001', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.0-flash-lite-001  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.0-flash-lite-001', 'gemini-2.0-flash-lite-001', 'Gemini 2.0 flash lite 001', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7.5e-05, 0.0003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.5-flash  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.5-flash', 'gemini-2.5-flash', 'Gemini 2.5 flash', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0025,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.5-flash-image  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.5-flash-image', 'gemini-2.5-flash-image', 'Gemini 2.5 flash image', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.03,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.5-flash-lite  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.5-flash-lite', 'gemini-2.5-flash-lite', 'Gemini 2.5 flash lite', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.5-flash-lite-preview-09-2025  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.5-flash-lite-preview-09-2025', 'gemini-2.5-flash-lite-preview-09-2025', 'Gemini 2.5 flash lite preview 09 2025', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.5-pro  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.5-pro', 'gemini-2.5-pro', 'Gemini 2.5 pro', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00125, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.5-pro-preview  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.5-pro-preview', 'gemini-2.5-pro-preview', 'Gemini 2.5 pro preview', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00125, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.5-pro-preview-05-06  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.5-pro-preview-05-06', 'gemini-2.5-pro-preview-05-06', 'Gemini 2.5 pro preview 05 06', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00125, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-3-flash-preview  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-3-flash-preview', 'gemini-3-flash-preview', 'Gemini 3 flash preview', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0005, 0.003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-3.1-flash-image-preview  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-3.1-flash-image-preview', 'gemini-3.1-flash-image-preview', 'Gemini 3.1 flash image preview', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0005, 0.049585,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-3.1-flash-lite-preview  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-3.1-flash-lite-preview', 'gemini-3.1-flash-lite-preview', 'Gemini 3.1 flash lite preview', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00025, 0.0015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-3.1-pro-preview  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-3.1-pro-preview', 'gemini-3.1-pro-preview', 'Gemini 3.1 pro preview', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.012,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemma-2-27b-it  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemma-2-27b-it', 'gemma-2-27b-it', 'Gemma 2 27b it', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00065, 0.00065,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemma-3-12b-it  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemma-3-12b-it', 'gemma-3-12b-it', 'Gemma 3 12b it', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    4e-05, 0.00013,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemma-3-27b-it  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemma-3-27b-it', 'gemma-3-27b-it', 'Gemma 3 27b it', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    8e-05, 0.00016,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemma-3-4b-it  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemma-3-4b-it', 'gemma-3-4b-it', 'Gemma 3 4b it', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    4e-05, 8e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemma-3n-e4b-it  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemma-3n-e4b-it', 'gemma-3n-e4b-it', 'Gemma 3n e4b it', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    2e-05, 4e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemma-4-26b-a4b-it  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemma-4-26b-a4b-it', 'gemma-4-26b-a4b-it', 'Gemma 4 26b a4b it', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00013, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- gryphe/mythomax-l2-13b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'gryphe/mythomax-l2-13b', 'mythomax-l2-13b', 'mythomax l2 13b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    6e-05, 6e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- ibm-granite/granite-4.0-h-micro  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'ibm-granite/granite-4.0-h-micro', 'granite-4.0-h-micro', 'granite 4.0 h micro', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    1.7e-05, 0.00011,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- inception/mercury  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'inception/mercury', 'mercury', 'mercury', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00025, 0.00075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- inception/mercury-2  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'inception/mercury-2', 'mercury-2', 'mercury 2', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00025, 0.00075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- inception/mercury-coder  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'inception/mercury-coder', 'mercury-coder', 'mercury coder', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00025, 0.00075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- inflection/inflection-3-productivity  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'inflection/inflection-3-productivity', 'inflection-3-productivity', 'inflection 3 productivity', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0025, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- kwaipilot/kat-coder-pro-v2  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'kwaipilot/kat-coder-pro-v2', 'kat-coder-pro-v2', 'kat coder pro v2', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0012,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mancer/weaver  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mancer/weaver', 'weaver', 'weaver', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00075, 0.001,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meituan/longcat-flash-chat  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meituan/longcat-flash-chat', 'longcat-flash-chat', 'longcat flash chat', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0008,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3-70b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3-70b-instruct', 'llama-3-70b-instruct', 'Llama 3 70b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00051, 0.00074,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3-8b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3-8b-instruct', 'llama-3-8b-instruct', 'Llama 3 8b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    3e-05, 4e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3.1-70b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3.1-70b-instruct', 'llama-3.1-70b-instruct', 'Llama 3.1 70b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0004, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3.1-8b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3.1-8b-instruct', 'llama-3.1-8b-instruct', 'Llama 3.1 8b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    2e-05, 5e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3.2-11b-vision-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3.2-11b-vision-instruct', 'llama-3.2-11b-vision-instruct', 'Llama 3.2 11b vision instruct', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    4.9e-05, 4.9e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3.2-1b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3.2-1b-instruct', 'llama-3.2-1b-instruct', 'Llama 3.2 1b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    2.7e-05, 0.0002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3.2-3b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3.2-3b-instruct', 'llama-3.2-3b-instruct', 'Llama 3.2 3b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    5.1e-05, 0.00034,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-3.3-70b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-3.3-70b-instruct', 'llama-3.3-70b-instruct', 'Llama 3.3 70b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.00032,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-4-maverick  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-4-maverick', 'llama-4-maverick', 'Llama 4 maverick', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-4-scout  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-4-scout', 'llama-4-scout', 'Llama 4 scout', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    8e-05, 0.0003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-guard-3-8b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-guard-3-8b', 'llama-guard-3-8b', 'Llama guard 3 8b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    2e-05, 6e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- meta-llama/llama-guard-4-12b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'meta-llama/llama-guard-4-12b', 'llama-guard-4-12b', 'Llama guard 4 12b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00018, 0.00018,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- microsoft/phi-4  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'microsoft/phi-4', 'phi-4', 'phi 4', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    6.5e-05, 0.00014,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- microsoft/wizardlm-2-8x22b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'microsoft/wizardlm-2-8x22b', 'wizardlm-2-8x22b', 'wizardlm 2 8x22b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00062, 0.00062,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- minimax/minimax-01  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'minimax/minimax-01', 'minimax-01', 'minimax 01', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0011,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- minimax/minimax-m2-her  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'minimax/minimax-m2-her', 'minimax-m2-her', 'minimax m2 her', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0012,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/codestral-2508  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/codestral-2508', 'codestral-2508', 'codestral 2508', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0009,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/devstral-2512  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/devstral-2512', 'devstral-2512', 'devstral 2512', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0004, 0.002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/devstral-medium  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/devstral-medium', 'devstral-medium', 'devstral medium', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0004, 0.002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/devstral-small  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/devstral-small', 'devstral-small', 'devstral small', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/ministral-14b-2512  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/ministral-14b-2512', 'ministral-14b-2512', 'Ministral 14b 2512', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/ministral-3b-2512  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/ministral-3b-2512', 'ministral-3b-2512', 'Ministral 3b 2512', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0001,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/ministral-8b-2512  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/ministral-8b-2512', 'ministral-8b-2512', 'Ministral 8b 2512', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.00015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-7b-instruct-v0.1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-7b-instruct-v0.1', 'mistral-7b-instruct-v0.1', 'Mistral 7b instruct v0.1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00011, 0.00019,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-large  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-large', 'mistral-large', 'Mistral large', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-large-2407  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-large-2407', 'mistral-large-2407', 'Mistral large 2407', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-large-2411  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-large-2411', 'mistral-large-2411', 'Mistral large 2411', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-large-2512  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-large-2512', 'mistral-large-2512', 'Mistral large 2512', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0005, 0.0015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-medium-3  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-medium-3', 'mistral-medium-3', 'Mistral medium 3', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0004, 0.002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-medium-3.1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-medium-3.1', 'mistral-medium-3.1', 'Mistral medium 3.1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0004, 0.002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-nemo  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-nemo', 'mistral-nemo', 'Mistral nemo', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    2e-05, 4e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-saba  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-saba', 'mistral-saba', 'Mistral saba', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-small-24b-instruct-2501  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-small-24b-instruct-2501', 'mistral-small-24b-instruct-2501', 'Mistral small 24b instruct 2501', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    5e-05, 8e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-small-2603  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-small-2603', 'mistral-small-2603', 'Mistral small 2603', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-small-3.1-24b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-small-3.1-24b-instruct', 'mistral-small-3.1-24b-instruct', 'Mistral small 3.1 24b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    3e-05, 0.00011,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-small-3.2-24b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-small-3.2-24b-instruct', 'mistral-small-3.2-24b-instruct', 'Mistral small 3.2 24b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7.5e-05, 0.0002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mistral-small-creative  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mistral-small-creative', 'mistral-small-creative', 'Mistral small creative', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mixtral-8x22b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mixtral-8x22b-instruct', 'mixtral-8x22b-instruct', 'Mixtral 8x22b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/mixtral-8x7b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/mixtral-8x7b-instruct', 'mixtral-8x7b-instruct', 'Mixtral 8x7b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00054, 0.00054,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/pixtral-large-2411  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/pixtral-large-2411', 'pixtral-large-2411', 'pixtral large 2411', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- mistralai/voxtral-small-24b-2507  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'mistralai/voxtral-small-24b-2507', 'voxtral-small-24b-2507', 'voxtral small 24b 2507', 'openrouter',
    ARRAY['text','audio']::modality_enum[], ARRAY['text','audio']::modality_enum[], ARRAY['text','audio']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-03', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- moonshotai/kimi-k2  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'moonshotai/kimi-k2', 'kimi-k2', 'kimi k2', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00057, 0.0023,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- moonshotai/kimi-k2-0905  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'moonshotai/kimi-k2-0905', 'kimi-k2-0905', 'kimi k2 0905', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0004, 0.002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- moonshotai/kimi-k2-thinking  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'moonshotai/kimi-k2-thinking', 'kimi-k2-thinking', 'kimi k2 thinking', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00047, 0.002,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route; supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- moonshotai/kimi-k2.5  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'moonshotai/kimi-k2.5', 'kimi-k2.5', 'kimi k2.5', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003827, 0.00172,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-07', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- morph/morph-v3-fast  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'morph/morph-v3-fast', 'morph-v3-fast', 'morph v3 fast', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0008, 0.0012,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- morph/morph-v3-large  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'morph/morph-v3-large', 'morph-v3-large', 'morph v3 large', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0009, 0.0019,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- nex-agi/deepseek-v3.1-nex-n1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'nex-agi/deepseek-v3.1-nex-n1', 'deepseek-v3.1-nex-n1', 'DeepSeek v3.1 nex n1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000135, 0.0005,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- nousresearch/hermes-2-pro-llama-3-8b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'nousresearch/hermes-2-pro-llama-3-8b', 'hermes-2-pro-llama-3-8b', 'hermes 2 pro llama 3 8b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00014, 0.00014,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- nousresearch/hermes-3-llama-3.1-405b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'nousresearch/hermes-3-llama-3.1-405b', 'hermes-3-llama-3.1-405b', 'hermes 3 llama 3.1 405b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.001, 0.001,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- nousresearch/hermes-3-llama-3.1-70b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'nousresearch/hermes-3-llama-3.1-70b', 'hermes-3-llama-3.1-70b', 'hermes 3 llama 3.1 70b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- nousresearch/hermes-4-405b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'nousresearch/hermes-4-405b', 'hermes-4-405b', 'hermes 4 405b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.001, 0.003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- nousresearch/hermes-4-70b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'nousresearch/hermes-4-70b', 'hermes-4-70b', 'hermes 4 70b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00013, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- nvidia/llama-3.1-nemotron-70b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'nvidia/llama-3.1-nemotron-70b-instruct', 'llama-3.1-nemotron-70b-instruct', 'Llama 3.1 nemotron 70b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0012, 0.0012,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- nvidia/llama-3.1-nemotron-ultra-253b-v1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'nvidia/llama-3.1-nemotron-ultra-253b-v1', 'llama-3.1-nemotron-ultra-253b-v1', 'Llama 3.1 nemotron ultra 253b v1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0006, 0.0018,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- nvidia/nemotron-3-nano-30b-a3b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'nvidia/nemotron-3-nano-30b-a3b', 'nemotron-3-nano-30b-a3b', 'nemotron 3 nano 30b a3b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    5e-05, 0.0002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-03', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- nvidia/nemotron-3-super-120b-a12b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'nvidia/nemotron-3-super-120b-a12b', 'nemotron-3-super-120b-a12b', 'nemotron 3 super 120b a12b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0005,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-3.5-turbo  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-3.5-turbo', 'gpt-3.5-turbo', 'GPT 3.5 turbo', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0005, 0.0015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-3.5-turbo-0613  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-3.5-turbo-0613', 'gpt-3.5-turbo-0613', 'GPT 3.5 turbo 0613', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.001, 0.002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-3.5-turbo-16k  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-3.5-turbo-16k', 'gpt-3.5-turbo-16k', 'GPT 3.5 turbo 16k', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-3.5-turbo-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-3.5-turbo-instruct', 'gpt-3.5-turbo-instruct', 'GPT 3.5 turbo instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0015, 0.002,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4', 'gpt-4', 'GPT 4', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.03, 0.06,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4-turbo  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4-turbo', 'gpt-4-turbo', 'GPT 4 turbo', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.01, 0.03,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4.1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4.1', 'gpt-4.1', 'GPT 4.1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.008,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4.1-mini  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4.1-mini', 'gpt-4.1-mini', 'GPT 4.1 mini', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0004, 0.0016,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4.1-nano  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4.1-nano', 'gpt-4.1-nano', 'GPT 4.1 nano', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4o  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4o', 'gpt-4o', 'GPT 4o', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0025, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4o-2024-05-13  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4o-2024-05-13', 'gpt-4o-2024-05-13', 'GPT 4o 2024 05 13', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.005, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4o-2024-08-06  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4o-2024-08-06', 'gpt-4o-2024-08-06', 'GPT 4o 2024 08 06', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0025, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4o-2024-11-20  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4o-2024-11-20', 'gpt-4o-2024-11-20', 'GPT 4o 2024 11 20', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0025, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4o-mini  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4o-mini', 'gpt-4o-mini', 'GPT 4o mini', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4o-mini-2024-07-18  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4o-mini-2024-07-18', 'gpt-4o-mini-2024-07-18', 'GPT 4o mini 2024 07 18', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4o-mini-search-preview  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4o-mini-search-preview', 'gpt-4o-mini-search-preview', 'GPT 4o mini search preview', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-4o-search-preview  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-4o-search-preview', 'gpt-4o-search-preview', 'GPT 4o search preview', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0025, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5-chat  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5-chat', 'gpt-5-chat', 'GPT 5 chat', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00125, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.1', 'gpt-5.1', 'GPT 5.1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00125, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.1-chat  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.1-chat', 'gpt-5.1-chat', 'GPT 5.1 chat', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00125, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.1-codex  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.1-codex', 'gpt-5.1-codex', 'GPT 5.1 codex', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00125, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.2  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.2', 'gpt-5.2', 'GPT 5.2', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00175, 0.014,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.2-chat  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.2-chat', 'gpt-5.2-chat', 'GPT 5.2 chat', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00175, 0.014,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.2-codex  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.2-codex', 'gpt-5.2-codex', 'GPT 5.2 codex', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00175, 0.014,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.2-pro  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.2-pro', 'gpt-5.2-pro', 'GPT 5.2 pro', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.021, 0.168,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.3-chat  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.3-chat', 'gpt-5.3-chat', 'GPT 5.3 chat', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00175, 0.014,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.3-codex  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.3-codex', 'gpt-5.3-codex', 'GPT 5.3 codex', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00175, 0.014,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.4  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.4', 'gpt-5.4', 'GPT 5.4', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0025, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.4-mini  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.4-mini', 'gpt-5.4-mini', 'GPT 5.4 mini', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00075, 0.0045,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.4-nano  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.4-nano', 'gpt-5.4-nano', 'GPT 5.4 nano', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.00125,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-5.4-pro  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-5.4-pro', 'gpt-5.4-pro', 'GPT 5.4 pro', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.03, 0.18,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/gpt-oss-safeguard-20b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/gpt-oss-safeguard-20b', 'gpt-oss-safeguard-20b', 'GPT oss safeguard 20b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7.5e-05, 0.0003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-03', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openai/o3-pro  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openai/o3-pro', 'o3-pro', 'O3 pro', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.02, 0.08,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openrouter/auto  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openrouter/auto', 'auto', 'auto', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    NULL, NULL,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', 'routing/auto model — price determined at request time'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- openrouter/bodybuilder  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'openrouter/bodybuilder', 'bodybuilder', 'bodybuilder', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    NULL, NULL,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', 'routing/auto model — price determined at request time'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- perplexity/sonar  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'perplexity/sonar', 'sonar', 'sonar', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.001, 0.001,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- perplexity/sonar-pro  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'perplexity/sonar-pro', 'sonar-pro', 'sonar pro', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- perplexity/sonar-pro-search  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'perplexity/sonar-pro-search', 'sonar-pro-search', 'sonar pro search', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-2.5-72b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-2.5-72b-instruct', 'qwen-2.5-72b-instruct', 'Qwen 2.5 72b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00012, 0.00039,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-2.5-7b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-2.5-7b-instruct', 'qwen-2.5-7b-instruct', 'Qwen 2.5 7b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    4e-05, 0.0001,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-2.5-coder-32b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-2.5-coder-32b-instruct', 'qwen-2.5-coder-32b-instruct', 'Qwen 2.5 coder 32b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00066, 0.001,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-max  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-max', 'qwen-max', 'Qwen max', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00104, 0.00416,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus', 'qwen-plus', 'Qwen plus', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00026, 0.00078,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus-2025-07-28  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus-2025-07-28', 'qwen-plus-2025-07-28', 'Qwen plus 2025 07 28', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00026, 0.00078,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus-2025-07-28:thinking  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus-2025-07-28:thinking', 'qwen-plus-2025-07-28', 'Qwen plus 2025 07 28', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00026, 0.00078,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route; supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-turbo  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-turbo', 'qwen-turbo', 'Qwen turbo', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    3.25e-05, 0.00013,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-vl-max  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-vl-max', 'qwen-vl-max', 'Qwen vl max', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00052, 0.00208,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-vl-plus  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-vl-plus', 'qwen-vl-plus', 'Qwen vl plus', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001365, 0.0004095,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen2.5-coder-7b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen2.5-coder-7b-instruct', 'qwen2.5-coder-7b-instruct', 'Qwen2.5 coder 7b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    3e-05, 9e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen2.5-vl-32b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen2.5-vl-32b-instruct', 'qwen2.5-vl-32b-instruct', 'Qwen2.5 vl 32b instruct', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-235b-a22b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-235b-a22b', 'qwen3-235b-a22b', 'Qwen3 235b a22b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000455, 0.00182,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-235b-a22b-2507  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-235b-a22b-2507', 'qwen3-235b-a22b-2507', 'Qwen3 235b a22b 2507', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7.1e-05, 0.0001,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-235b-a22b-thinking-2507  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-235b-a22b-thinking-2507', 'qwen3-235b-a22b-thinking-2507', 'Qwen3 235b a22b thinking 2507', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001495, 0.001495,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-30b-a3b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-30b-a3b', 'qwen3-30b-a3b', 'Qwen3 30b a3b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    8e-05, 0.00028,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-30b-a3b-instruct-2507  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-30b-a3b-instruct-2507', 'qwen3-30b-a3b-instruct-2507', 'Qwen3 30b a3b instruct 2507', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    9e-05, 0.0003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-32b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-32b', 'qwen3-32b', 'Qwen3 32b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    8e-05, 0.00024,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-8b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-8b', 'qwen3-8b', 'Qwen3 8b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    5e-05, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder', 'qwen3-coder', 'Qwen3 coder', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00022, 0.001,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-30b-a3b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-30b-a3b-instruct', 'qwen3-coder-30b-a3b-instruct', 'Qwen3 coder 30b a3b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7e-05, 0.00027,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-flash  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-flash', 'qwen3-coder-flash', 'Qwen3 coder flash', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000195, 0.000975,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-next  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-next', 'qwen3-coder-next', 'Qwen3 coder next', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00012, 0.00075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-plus  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-plus', 'qwen3-coder-plus', 'Qwen3 coder plus', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00065, 0.00325,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-max  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-max', 'qwen3-max', 'Qwen3 max', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00078, 0.0039,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-max-thinking  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-max-thinking', 'qwen3-max-thinking', 'Qwen3 max thinking', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00078, 0.0039,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-next-80b-a3b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-next-80b-a3b-instruct', 'qwen3-next-80b-a3b-instruct', 'Qwen3 next 80b a3b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    9e-05, 0.0011,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-next-80b-a3b-thinking  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-next-80b-a3b-thinking', 'qwen3-next-80b-a3b-thinking', 'Qwen3 next 80b a3b thinking', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    9.75e-05, 0.00078,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-235b-a22b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-235b-a22b-instruct', 'qwen3-vl-235b-a22b-instruct', 'Qwen3 vl 235b a22b instruct', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.00088,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-235b-a22b-thinking  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-235b-a22b-thinking', 'qwen3-vl-235b-a22b-thinking', 'Qwen3 vl 235b a22b thinking', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00026, 0.0026,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-30b-a3b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-30b-a3b-instruct', 'qwen3-vl-30b-a3b-instruct', 'Qwen3 vl 30b a3b instruct', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00013, 0.00052,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-30b-a3b-thinking  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-30b-a3b-thinking', 'qwen3-vl-30b-a3b-thinking', 'Qwen3 vl 30b a3b thinking', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00013, 0.00156,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-32b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-32b-instruct', 'qwen3-vl-32b-instruct', 'Qwen3 vl 32b instruct', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000104, 0.000416,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-8b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-8b-instruct', 'qwen3-vl-8b-instruct', 'Qwen3 vl 8b instruct', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    8e-05, 0.0005,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-8b-thinking  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-8b-thinking', 'qwen3-vl-8b-thinking', 'Qwen3 vl 8b thinking', 'openrouter',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000117, 0.001365,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-122b-a10b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-122b-a10b', 'qwen3.5-122b-a10b', 'Qwen3.5 122b a10b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00026, 0.00208,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-27b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-27b', 'qwen3.5-27b', 'Qwen3.5 27b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000195, 0.00156,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-35b-a3b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-35b-a3b', 'qwen3.5-35b-a3b', 'Qwen3.5 35b a3b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001625, 0.0013,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-397b-a17b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-397b-a17b', 'qwen3.5-397b-a17b', 'Qwen3.5 397b a17b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00039, 0.00234,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    FALSE, TRUE, '2026-04-09', 'non-default route'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-flash-02-23  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-flash-02-23', 'qwen3.5-flash-02-23', 'Qwen3.5 flash 02 23', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    6.5e-05, 0.00026,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-plus-02-15  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-plus-02-15', 'qwen3.5-plus-02-15', 'Qwen3.5 plus 02 15', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00026, 0.00156,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwq-32b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwq-32b', 'qwq-32b', 'qwq 32b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.00058,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- rekaai/reka-edge  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'rekaai/reka-edge', 'reka-edge', 'reka edge', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0001,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- relace/relace-search  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'relace/relace-search', 'relace-search', 'relace search', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.001, 0.003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- sao10k/l3-euryale-70b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'sao10k/l3-euryale-70b', 'l3-euryale-70b', 'l3 euryale 70b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00148, 0.00148,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- sao10k/l3-lunaris-8b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'sao10k/l3-lunaris-8b', 'l3-lunaris-8b', 'l3 lunaris 8b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    4e-05, 5e-05,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- sao10k/l3.1-70b-hanami-x1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'sao10k/l3.1-70b-hanami-x1', 'l3.1-70b-hanami-x1', 'l3.1 70b hanami x1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- sao10k/l3.1-euryale-70b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'sao10k/l3.1-euryale-70b', 'l3.1-euryale-70b', 'l3.1 euryale 70b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00085, 0.00085,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- sao10k/l3.3-euryale-70b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'sao10k/l3.3-euryale-70b', 'l3.3-euryale-70b', 'l3.3 euryale 70b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00065, 0.00075,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- stepfun/step-3.5-flash  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'stepfun/step-3.5-flash', 'step-3.5-flash', 'step 3.5 flash', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0003,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- switchpoint/router  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'switchpoint/router', 'router', 'router', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00085, 0.0034,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- tencent/hunyuan-a13b-instruct  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'tencent/hunyuan-a13b-instruct', 'hunyuan-a13b-instruct', 'hunyuan a13b instruct', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00014, 0.00057,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- thedrummer/cydonia-24b-v4.1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'thedrummer/cydonia-24b-v4.1', 'cydonia-24b-v4.1', 'cydonia 24b v4.1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0005,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- thedrummer/rocinante-12b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'thedrummer/rocinante-12b', 'rocinante-12b', 'rocinante 12b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00017, 0.00043,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- thedrummer/skyfall-36b-v2  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'thedrummer/skyfall-36b-v2', 'skyfall-36b-v2', 'skyfall 36b v2', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00055, 0.0008,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- thedrummer/unslopnemo-12b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'thedrummer/unslopnemo-12b', 'unslopnemo-12b', 'unslopnemo 12b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0004, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- undi95/remm-slerp-l2-13b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'undi95/remm-slerp-l2-13b', 'remm-slerp-l2-13b', 'remm slerp l2 13b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00045, 0.00065,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- upstage/solar-pro-3  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'upstage/solar-pro-3', 'solar-pro-3', 'solar pro 3', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00015, 0.0006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- writer/palmyra-x5  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'writer/palmyra-x5', 'palmyra-x5', 'palmyra x5', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0006, 0.006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- x-ai/grok-3  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'x-ai/grok-3', 'grok-3', 'grok 3', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- x-ai/grok-3-beta  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'x-ai/grok-3-beta', 'grok-3-beta', 'grok 3 beta', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- x-ai/grok-3-mini  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'x-ai/grok-3-mini', 'grok-3-mini', 'grok 3 mini', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0005,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- x-ai/grok-3-mini-beta  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'x-ai/grok-3-mini-beta', 'grok-3-mini-beta', 'grok 3 mini beta', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0005,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- x-ai/grok-4  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'x-ai/grok-4', 'grok-4', 'grok 4', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.003, 0.015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- x-ai/grok-4-fast  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'x-ai/grok-4-fast', 'grok-4-fast', 'grok 4 fast', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0005,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- x-ai/grok-4.1-fast  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'x-ai/grok-4.1-fast', 'grok-4.1-fast', 'grok 4.1 fast', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0005,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- x-ai/grok-4.20  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'x-ai/grok-4.20', 'grok-4.20', 'grok 4.20', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- x-ai/grok-4.20-multi-agent  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'x-ai/grok-4.20-multi-agent', 'grok-4.20-multi-agent', 'grok 4.20 multi agent', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.002, 0.006,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- x-ai/grok-code-fast-1  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'x-ai/grok-code-fast-1', 'grok-code-fast-1', 'grok code fast 1', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0002, 0.0015,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- xiaomi/mimo-v2-flash  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'xiaomi/mimo-v2-flash', 'mimo-v2-flash', 'mimo v2 flash', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    9e-05, 0.00029,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-03', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- z-ai/glm-4-32b  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'z-ai/glm-4-32b', 'glm-4-32b', 'glm 4 32b', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0001,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- z-ai/glm-4.5-air  [openrouter]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'z-ai/glm-4.5-air', 'glm-4.5-air', 'glm 4.5 air', 'openrouter',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00013, 0.00085,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-flash  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-flash', 'qwen-flash', 'Qwen flash', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    2.2e-05, 0.000216,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-flash-2025-07-28  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-flash-2025-07-28', 'qwen-flash-2025-07-28', 'Qwen flash 2025 07 28', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    2.2e-05, 0.000216,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-mt-flash  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-mt-flash', 'qwen-mt-flash', 'Qwen mt flash', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000101, 0.00028,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-mt-lite  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-mt-lite', 'qwen-mt-lite', 'Qwen mt lite', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    8.6e-05, 0.000229,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-mt-plus  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-mt-plus', 'qwen-mt-plus', 'Qwen mt plus', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000259, 0.000775,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus', 'qwen-plus', 'Qwen plus', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000115, 0.000287,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus-2025-07-28  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus-2025-07-28', 'qwen-plus-2025-07-28', 'Qwen plus 2025 07 28', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000345, 0.002868,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus-2025-07-28:non-thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus-2025-07-28:non-thinking', 'qwen-plus-2025-07-28', 'Qwen plus 2025 07 28', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000115, 0.000287,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus-2025-07-28:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus-2025-07-28:thinking', 'qwen-plus-2025-07-28', 'Qwen plus 2025 07 28', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000115, 0.001147,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus-2025-09-11  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus-2025-09-11', 'qwen-plus-2025-09-11', 'Qwen plus 2025 09 11', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000345, 0.002868,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus-2025-09-11:non-thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus-2025-09-11:non-thinking', 'qwen-plus-2025-09-11', 'Qwen plus 2025 09 11', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000115, 0.000287,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus-2025-09-11:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus-2025-09-11:thinking', 'qwen-plus-2025-09-11', 'Qwen plus 2025 09 11', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000115, 0.001147,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus-2025-12-01  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus-2025-12-01', 'qwen-plus-2025-12-01', 'Qwen plus 2025 12 01', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000115, 0.000287,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus-2025-12-01:non-thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus-2025-12-01:non-thinking', 'qwen-plus-2025-12-01', 'Qwen plus 2025 12 01', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000345, 0.002868,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus-2025-12-01:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus-2025-12-01:thinking', 'qwen-plus-2025-12-01', 'Qwen plus 2025 12 01', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000115, 0.001147,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus:non-thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus:non-thinking', 'qwen-plus', 'Qwen plus', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000689, 0.006881,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen-plus:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen-plus:thinking', 'qwen-plus', 'Qwen plus', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000115, 0.001147,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-14b:non-thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-14b:non-thinking', 'qwen3-14b', 'Qwen3 14b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000144, 0.000574,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-14b:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-14b:thinking', 'qwen3-14b', 'Qwen3 14b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000144, 0.001434,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-235b-a22b-instruct-2507  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-235b-a22b-instruct-2507', 'qwen3-235b-a22b-instruct-2507', 'Qwen3 235b a22b instruct 2507', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00023, 0.00092,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-235b-a22b:non-thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-235b-a22b:non-thinking', 'qwen3-235b-a22b', 'Qwen3 235b a22b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000287, 0.001147,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-235b-a22b:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-235b-a22b:thinking', 'qwen3-235b-a22b', 'Qwen3 235b a22b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000287, 0.002868,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-30b-a3b-instruct-2507  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-30b-a3b-instruct-2507', 'qwen3-30b-a3b-instruct-2507', 'Qwen3 30b a3b instruct 2507', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000108, 0.000431,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-30b-a3b:non-thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-30b-a3b:non-thinking', 'qwen3-30b-a3b', 'Qwen3 30b a3b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000108, 0.000431,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-30b-a3b:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-30b-a3b:thinking', 'qwen3-30b-a3b', 'Qwen3 30b a3b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000108, 0.001076,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-32b:non-thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-32b:non-thinking', 'qwen3-32b', 'Qwen3 32b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00016, 0.00064,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-32b:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-32b:thinking', 'qwen3-32b', 'Qwen3 32b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00016, 0.00064,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-8b:non-thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-8b:non-thinking', 'qwen3-8b', 'Qwen3 8b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7.2e-05, 0.000287,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-8b:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-8b:thinking', 'qwen3-8b', 'Qwen3 8b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7.2e-05, 0.000717,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-30b-a3b-instruct  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-30b-a3b-instruct', 'qwen3-coder-30b-a3b-instruct', 'Qwen3 coder 30b a3b instruct', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000216, 0.000861,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-480b-a35b-instruct  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-480b-a35b-instruct', 'qwen3-coder-480b-a35b-instruct', 'Qwen3 coder 480b a35b instruct', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000861, 0.003441,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-flash  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-flash', 'qwen3-coder-flash', 'Qwen3 coder flash', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000144, 0.000574,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-flash-2025-07-28  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-flash-2025-07-28', 'qwen3-coder-flash-2025-07-28', 'Qwen3 coder flash 2025 07 28', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000144, 0.000574,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-plus  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-plus', 'qwen3-coder-plus', 'Qwen3 coder plus', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000574, 0.002294,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-plus-2025-07-22  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-plus-2025-07-22', 'qwen3-coder-plus-2025-07-22', 'Qwen3 coder plus 2025 07 22', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000574, 0.002294,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-coder-plus-2025-09-23  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-coder-plus-2025-09-23', 'qwen3-coder-plus-2025-09-23', 'Qwen3 coder plus 2025 09 23', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000574, 0.002294,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-max  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-max', 'qwen3-max', 'Qwen3 max', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000359, 0.001434,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-max-2025-09-23  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-max-2025-09-23', 'qwen3-max-2025-09-23', 'Qwen3 max 2025 09 23', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000861, 0.003441,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-max-2026-01-23  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-max-2026-01-23', 'qwen3-max-2026-01-23', 'Qwen3 max 2026 01 23', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000359, 0.001434,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    FALSE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'responses API only; responses_provider_model_id=qwen3-max-2026-01-23'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-max-preview  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-max-preview', 'qwen3-max-preview', 'Qwen3 max preview', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000861, 0.003441,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-next-80b-a3b-instruct  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-next-80b-a3b-instruct', 'qwen3-next-80b-a3b-instruct', 'Qwen3 next 80b a3b instruct', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000144, 0.000574,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-235b-a22b-instruct  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-235b-a22b-instruct', 'qwen3-vl-235b-a22b-instruct', 'Qwen3 vl 235b a22b instruct', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000287, 0.001147,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-235b-a22b-thinking:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-235b-a22b-thinking:thinking', 'qwen3-vl-235b-a22b-thinking', 'Qwen3 vl 235b a22b thinking', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000287, 0.002868,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-30b-a3b-instruct  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-30b-a3b-instruct', 'qwen3-vl-30b-a3b-instruct', 'Qwen3 vl 30b a3b instruct', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000108, 0.000431,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-30b-a3b-thinking:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-30b-a3b-thinking:thinking', 'qwen3-vl-30b-a3b-thinking', 'Qwen3 vl 30b a3b thinking', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000108, 0.001076,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-32b-instruct  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-32b-instruct', 'qwen3-vl-32b-instruct', 'Qwen3 vl 32b instruct', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00016, 0.00064,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-32b-thinking:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-32b-thinking:thinking', 'qwen3-vl-32b-thinking', 'Qwen3 vl 32b thinking', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00016, 0.00064,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-8b-instruct  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-8b-instruct', 'qwen3-vl-8b-instruct', 'Qwen3 vl 8b instruct', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7.2e-05, 0.000287,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-8b-thinking:thinking  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-8b-thinking:thinking', 'qwen3-vl-8b-thinking', 'Qwen3 vl 8b thinking', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    7.2e-05, 0.000717,
    FALSE, FALSE, TRUE,
    TRUE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', 'supports thinking/reasoning mode'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-flash  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-flash', 'qwen3-vl-flash', 'Qwen3 vl flash', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    2.2e-05, 0.000215,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-flash-2025-10-15  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-flash-2025-10-15', 'qwen3-vl-flash-2025-10-15', 'Qwen3 vl flash 2025 10 15', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    2.2e-05, 0.000215,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-plus  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-plus', 'qwen3-vl-plus', 'Qwen3 vl plus', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000144, 0.001434,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3-vl-plus-2025-09-23  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3-vl-plus-2025-09-23', 'qwen3-vl-plus-2025-09-23', 'Qwen3 vl plus 2025 09 23', 'qwen',
    ARRAY['text','image']::modality_enum[], ARRAY['text','image']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000144, 0.001434,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-122b-a10b  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-122b-a10b', 'qwen3.5-122b-a10b', 'Qwen3.5 122b a10b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000115, 0.000917,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-27b  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-27b', 'qwen3.5-27b', 'Qwen3.5 27b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    8.6e-05, 0.000688,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-35b-a3b  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-35b-a3b', 'qwen3.5-35b-a3b', 'Qwen3.5 35b a3b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    5.7e-05, 0.000459,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-397b-a17b  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-397b-a17b', 'qwen3.5-397b-a17b', 'Qwen3.5 397b a17b', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000172, 0.001032,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-flash  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-flash', 'qwen3.5-flash', 'Qwen3.5 flash', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    2.9e-05, 0.000287,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-flash-2026-02-23  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-flash-2026-02-23', 'qwen3.5-flash-2026-02-23', 'Qwen3.5 flash 2026 02 23', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    2.9e-05, 0.000287,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-plus  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-plus', 'qwen3.5-plus', 'Qwen3.5 plus', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000115, 0.000688,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.5-plus-2026-02-15  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.5-plus-2026-02-15', 'qwen3.5-plus-2026-02-15', 'Qwen3.5 plus 2026 02 15', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000115, 0.000688,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.6-plus  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.6-plus', 'qwen3.6-plus', 'Qwen3.6 plus', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000276, 0.001651,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- qwen/qwen3.6-plus-2026-04-02  [qwen]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'qwen/qwen3.6-plus-2026-04-02', 'qwen3.6-plus-2026-04-02', 'Qwen3.6 plus 2026 04 02', 'qwen',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.000276, 0.001651,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, TRUE, FALSE,
    TRUE, TRUE, '2026-04-13', 'completions + responses API'
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2-5-pro  [vertex]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2-5-pro', 'gemini-2.5-pro', 'Gemini 2 5 pro', 'vertex',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00125, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.5-flash  [vertex]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.5-flash', 'gemini-2.5-flash', 'Gemini 2.5 flash', 'vertex',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0003, 0.0025,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.5-flash-lite  [vertex]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.5-flash-lite', 'gemini-2.5-flash-lite', 'Gemini 2.5 flash lite', 'vertex',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.0001, 0.0004,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-09', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

-- google/gemini-2.5-pro  [vertex]
INSERT INTO model_pricing (
    model_id, provider_model_id, model_name, provider,
    modality, input_modalities, output_modalities,
    pricing_unit, currency,
    input_cost, output_cost,
    supports_tools, supports_structured_output, supports_system_prompt,
    supports_thinking, supports_batching,
    supports_completions_api, supports_responses_api, supports_embeddings,
    is_default, is_active, effective_date, notes
) VALUES (
    'google/gemini-2.5-pro', 'gemini-2.5-pro', 'Gemini 2.5 pro', 'vertex',
    ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[], ARRAY['text']::modality_enum[],
    'per_1k_tokens', 'USD',
    0.00125, 0.01,
    FALSE, FALSE, TRUE,
    FALSE, FALSE,
    TRUE, FALSE, FALSE,
    TRUE, TRUE, '2026-04-07', NULL
)
ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET
    input_cost               = EXCLUDED.input_cost,
    output_cost              = EXCLUDED.output_cost,
    provider_model_id        = EXCLUDED.provider_model_id,
    supports_thinking        = EXCLUDED.supports_thinking,
    supports_batching         = EXCLUDED.supports_batching,
    supports_completions_api = EXCLUDED.supports_completions_api,
    supports_responses_api   = EXCLUDED.supports_responses_api,
    supports_embeddings      = EXCLUDED.supports_embeddings,
    is_default               = EXCLUDED.is_default,
    notes                    = EXCLUDED.notes,
    updated_at               = now();

COMMIT;

-- 387 rows processed
-- 2 routing/auto models had sentinel prices (-1000) → stored as NULL
