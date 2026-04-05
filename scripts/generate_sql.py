import os, httpx

PASSED = open("passed_20260402_144542.txt").read().strip().splitlines()
passed = set(PASSED)

resp = httpx.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
    timeout=30,
)
resp.raise_for_status()
models = {m["id"]: m for m in resp.json()["data"]}

print("BEGIN;")
print()

for model_id in sorted(passed):
    m = models.get(model_id)
    if not m:
        print(f"-- WARNING: {model_id} not found in OpenRouter catalog, skipping")
        continue

    name             = (m.get("name") or model_id).replace("'", "''")
    ctx              = m.get("context_length")
    desc             = (m.get("description") or "").replace("'", "''")
    p                = m.get("pricing") or {}
    prompt_1k        = round(float(p.get("prompt") or 0) * 1000, 8)
    completion_1k    = round(float(p.get("completion") or 0) * 1000, 8)
    is_free          = "true" if prompt_1k == 0 and completion_1k == 0 else "false"
    ctx_sql          = str(ctx) if ctx else "NULL"
    desc_sql         = f"'{desc}'" if desc else "NULL"

    print(f"INSERT INTO models (model_id, name, context_length, description, is_enabled) VALUES ('{model_id}', '{name}', {ctx_sql}, {desc_sql}, true);")
    print(f"INSERT INTO model_prices (model_id, provider, is_default, prompt_usd_per_1k, completion_usd_per_1k, is_free) VALUES ('{model_id}', 'openrouter', true, {prompt_1k}, {completion_1k}, {is_free});")
    print()

print("COMMIT;")
