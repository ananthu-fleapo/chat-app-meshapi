#!/usr/bin/env python3
"""
generate_model_pricing_inserts.py
----------------------------------
Reads the model_prices JSON (from stdin or a file path argument) and emits
a ready-to-run PostgreSQL INSERT script for the model_pricing table.

Usage:
    python3 generate_model_pricing_inserts.py model_prices.json > inserts.sql
    cat model_prices.json | python3 generate_model_pricing_inserts.py > inserts.sql
"""

import json
import re
import sys
from datetime import datetime, timezone


# ── helpers ──────────────────────────────────────────────────────────────────

def esc(s):
    """Escape a Python value as a SQL string literal, or NULL."""
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

def sql_bool(v):
    return "TRUE" if v else "FALSE"

def sql_numeric(v):
    """Return a SQL numeric literal, or NULL."""
    if v is None:
        return "NULL"
    return repr(float(v))

def derive_model_name(model_id: str) -> str:
    """
    Turn 'openai/gpt-4o-2024-08-06' → 'GPT-4o 2024-08-06'
    Best-effort; downstream can always override.
    """
    slug = model_id.split("/", 1)[-1]        # drop org prefix
    slug = re.sub(r":[a-z\-]+$", "", slug)   # strip :thinking / :non-thinking

    prefixes = [
        ("gpt-",       "GPT-"),
        ("claude-",    "Claude "),
        ("gemini-",    "Gemini "),
        ("gemma-",     "Gemma "),
        ("llama-",     "Llama "),
        ("llama3",     "Llama 3"),
        ("mistral-",   "Mistral "),
        ("magistral-", "Magistral "),
        ("ministral-", "Ministral "),
        ("mixtral-",   "Mixtral "),
        ("qwen",       "Qwen"),
        ("deepseek-",  "DeepSeek "),
        ("nova-",      "Nova "),
        ("o1",         "O1"),
        ("o3",         "O3"),
        ("o4",         "O4"),
    ]
    name = slug
    for src, dst in prefixes:
        if name.lower().startswith(src.lower()):
            name = dst + name[len(src):]
            break
    # Replace hyphens with spaces for readability, preserve version numbers
    name = name.replace("-", " ").strip()
    return name

def infer_modalities(model_id: str, row: dict) -> tuple[list[str], list[str], list[str]]:
    """
    Return (all_modalities, input_modalities, output_modalities).
    """
    slug = model_id.lower()

    is_embedding    = row.get("supports_embeddings_api", False)
    is_vision       = any(x in slug for x in ["vl-", "-vl", "vision", "pixtral", "image",
                                               "dall-e", "gemma-3n", "gemma-3", "llama-3.2-11b"])
    is_transcription = any(x in slug for x in ["whisper"])
    is_audio_io     = any(x in slug for x in ["voxtral", "realtime"])

    if is_embedding:
        return ["embedding"], ["text"], ["embedding"]
    if is_transcription:
        return ["transcription", "audio", "text"], ["audio"], ["text"]
    if is_audio_io:
        return ["text", "audio"], ["text", "audio"], ["text", "audio"]
    if is_vision:
        return ["text", "image"], ["text", "image"], ["text"]
    return ["text"], ["text"], ["text"]

def pg_text_array(values: list[str], cast: str) -> str:
    """Return a Postgres array literal like ARRAY['text','image']::modality_enum[]"""
    inner = ",".join(f"'{v}'" for v in values)
    return f"ARRAY[{inner}]::{cast}"

def effective_date(updated_at: str) -> str:
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        return "'" + dt.strftime("%Y-%m-%d") + "'"
    except Exception:
        return "'2024-01-01'"

def fallback_provider_model_id(row: dict) -> str:
    """If provider_model_id is null in the source, derive it from the model_id slug."""
    pmid = row.get("provider_model_id")
    if pmid:
        return pmid
    slug = row["model_id"].split("/", 1)[-1]
    return re.sub(r":[a-z\-]+$", "", slug)

def build_notes(row: dict) -> str | None:
    parts = []
    if row.get("is_free"):
        parts.append("free tier")
    if not row.get("is_default"):
        parts.append("non-default route")
    if row.get("supports_thinking"):
        parts.append("supports thinking/reasoning mode")
    if row.get("supports_completions_api") and row.get("supports_responses_api"):
        parts.append("completions + responses API")
    elif row.get("supports_responses_api"):
        parts.append("responses API only")
    elif not row.get("supports_completions_api"):
        parts.append("completions API not supported")
    resp_id = row.get("responses_provider_model_id")
    if resp_id:
        parts.append(f"responses_provider_model_id={resp_id}")
    return "; ".join(parts) if parts else None

def is_sentinel_price(v) -> bool:
    """OpenRouter uses -1000 as a sentinel for 'price varies / routing model'."""
    return v is not None and float(v) < 0


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    # Read input
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    rows = data["model_prices"]

    # Deduplicate: keep the most recently updated row per (model_id, provider)
    seen: dict[tuple, dict] = {}
    for row in rows:
        key = (row["model_id"], row["provider"])
        existing = seen.get(key)
        if existing is None or row["updated_at"] > existing["updated_at"]:
            seen[key] = row

    deduped = sorted(seen.values(), key=lambda r: (r["provider"], r["model_id"]))

    # ── output ────────────────────────────────────────────────────────────────
    out = []
    out.append("-- ================================================================")
    out.append("-- model_pricing — generated INSERT statements")
    out.append(f"-- Source rows   : {len(rows)}")
    out.append(f"-- After dedup   : {len(deduped)}  (unique model_id + provider)")
    out.append(f"-- Generated     : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    out.append("-- Strategy      : ON CONFLICT (model_id, provider, effective_date)")
    out.append("--                 DO UPDATE to refresh costs + notes")
    out.append("-- ================================================================")
    out.append("")
    out.append("BEGIN;")
    out.append("")

    sentinel_count = 0

    for row in deduped:
        model_id    = row["model_id"]
        provider    = row["provider"]
        pmid        = fallback_provider_model_id(row)
        model_name  = derive_model_name(model_id)
        all_m, in_m, out_m = infer_modalities(model_id, row)
        modality_col  = pg_text_array(all_m,  "modality_enum[]")
        input_m_col   = pg_text_array(in_m,   "modality_enum[]")
        output_m_col  = pg_text_array(out_m,  "modality_enum[]")
        eff_date      = effective_date(row.get("updated_at", ""))
        notes         = build_notes(row)

        ic = row.get("prompt_usd_per_1k")
        oc = row.get("completion_usd_per_1k")

        # Sentinel prices: store as NULL and note it
        if is_sentinel_price(ic) or is_sentinel_price(oc):
            sentinel_count += 1
            extra = "routing/auto model — price determined at request time"
            notes = (notes + "; " + extra) if notes else extra
            ic_sql = "NULL"
            oc_sql = "NULL"
        else:
            ic_sql = sql_numeric(ic)
            oc_sql = sql_numeric(oc)

        out.append(f"-- {model_id}  [{provider}]")
        out.append( "INSERT INTO model_pricing (")
        out.append( "    model_id, provider_model_id, model_name, provider,")
        out.append( "    modality, input_modalities, output_modalities,")
        out.append( "    pricing_unit, currency,")
        out.append( "    input_cost, output_cost,")
        out.append( "    supports_tools, supports_structured_output, supports_system_prompt,")
        out.append( "    supports_thinking, supports_batching,")
        out.append( "    supports_completions_api, supports_responses_api, supports_embeddings,")
        out.append( "    is_default, is_active, effective_date, notes")
        out.append( ") VALUES (")
        out.append(f"    {esc(model_id)}, {esc(pmid)}, {esc(model_name)}, {esc(provider)},")
        out.append(f"    {modality_col}, {input_m_col}, {output_m_col},")
        out.append( "    'per_1k_tokens', 'USD',")
        out.append(f"    {ic_sql}, {oc_sql},")
        out.append( "    FALSE, FALSE, TRUE,")
        out.append(f"    {sql_bool(row.get('supports_thinking', False))}, {sql_bool(row.get('supports_batching', False))},")
        out.append(f"    {sql_bool(row.get('supports_completions_api', True))}, {sql_bool(row.get('supports_responses_api', False))}, {sql_bool(row.get('supports_embeddings_api', False))},")
        out.append(f"    {sql_bool(row.get('is_default', False))}, TRUE, {eff_date}, {esc(notes)}")
        out.append( ")")
        out.append( "ON CONFLICT (model_id, provider, effective_date) DO UPDATE SET")
        out.append( "    input_cost               = EXCLUDED.input_cost,")
        out.append( "    output_cost              = EXCLUDED.output_cost,")
        out.append( "    provider_model_id        = EXCLUDED.provider_model_id,")
        out.append( "    supports_thinking        = EXCLUDED.supports_thinking,")
        out.append( "    supports_batching         = EXCLUDED.supports_batching,")
        out.append( "    supports_completions_api = EXCLUDED.supports_completions_api,")
        out.append( "    supports_responses_api   = EXCLUDED.supports_responses_api,")
        out.append( "    supports_embeddings      = EXCLUDED.supports_embeddings,")
        out.append( "    is_default               = EXCLUDED.is_default,")
        out.append( "    notes                    = EXCLUDED.notes,")
        out.append( "    updated_at               = now();")
        out.append("")

    out.append("COMMIT;")
    out.append("")
    out.append(f"-- {len(deduped)} rows processed")
    if sentinel_count:
        out.append(f"-- {sentinel_count} routing/auto models had sentinel prices (-1000) → stored as NULL")

    print("\n".join(out))


if __name__ == "__main__":
    main()