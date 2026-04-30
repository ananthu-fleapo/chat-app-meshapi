# Coupons — Complete Flow Reference

## Overview

The coupon system lets admins create discount codes that users apply at checkout. **Stripe is the source of truth for coupons.** Our database is a local read-cache — a background sync job (cron + manual) pulls coupons from Stripe every 30 minutes. Admins can annotate synced records with local metadata (name, description, reuse policy, user targeting).

At checkout, the frontend passes `?provider=stripe` to filter the coupon list to coupons that exist in Stripe.

---

## Architecture

```
Stripe Dashboard
(create / manage)
        │
        ▼
POST /v1/admin/coupons/sync-all  (manual)
POST /v1/internal/coupons/sync   (cron, every 30 min)
        │
        ▼
checkout_coupons table (local cache)
Admin can annotate: name, description, reuse_policy, user_ids
        │
GET /v1/coupons?provider=stripe     → Stripe coupons only
        │
Payment webhook → increment used_count locally
                → auto-deactivate locally when max_uses reached
```

---

## Data Model

### `checkout_coupons`

| Column | Type | Source | Notes |
|---|---|---|---|
| `id` | UUID | local | Internal primary key |
| `code` | TEXT UNIQUE | PG / local | Always stored uppercase |
| `name` | TEXT | local | Admin-set; preserved across syncs |
| `description` | TEXT \| NULL | local | Admin-set; preserved across syncs |
| `discount_type` | TEXT | PG | `"percentage"` or `"flat"` — set by sync |
| `discount_value` | NUMERIC(12,2) | PG | Set by sync from PG data |
| `currency` | TEXT | PG | ISO-4217, default `"INR"` |
| `reuse_policy` | TEXT | local | `"single_use"` or `"reusable"` — our concept, not in PG |
| `max_uses` | INT \| NULL | PG | Set by sync; NULL = unlimited |
| `used_count` | INT | local | Incremented by payment webhook; also updated from Stripe `times_redeemed` on sync |
| `valid_till` | TIMESTAMPTZ \| NULL | PG | Set by sync |
| `is_active` | BOOL | PG + local | Set by sync; admin can also set `false` locally to hide a coupon |
| `stripe_synced_at` | TIMESTAMPTZ \| NULL | local | Last successful Stripe pull — `NOT NULL` means this coupon exists in Stripe |
| `created_at` / `updated_at` | TIMESTAMPTZ | local | Managed by DB |

> **Name and description are local-only.** They are set at creation (`POST /v1/admin/coupons`) or via update (`PATCH`). Sync never overwrites them — the PG data is authoritative only for discount fields.

### `coupon_users`

Maps which users are eligible for a targeted coupon. Empty = available to all.

| Column | Notes |
|---|---|
| `coupon_id` | FK → `checkout_coupons.id` |
| `user_id` | Supabase user ID |

### `coupon_sync_issues`

Persisted log of sync events for admin review.

| Column | Notes |
|---|---|
| `coupon_code` | Denormalized — survives coupon deletion |
| `provider` | `"stripe"` |
| `issue_type` | `"fetch_failed"` \| `"auto_deactivated"` \| `"mismatch"` |
| `details` | JSONB — error message or diff |
| `status` | `"pending"` \| `"resolved"` \| `"dismissed"` |

---

## Coupon Lifecycle

### 1. Admin creates a coupon in the Stripe dashboard

Log into the [Stripe Dashboard](https://dashboard.stripe.com/coupons) and create the coupon there. This is the canonical source — discount terms, validity, and usage limits are set here.

### 2. Sync pulls the coupon into our system

```
POST /v1/admin/coupons/sync-all   (manual trigger)
POST /v1/internal/coupons/sync    (cron, every 30 min, Authorization: Bearer <WEBHOOK_API_KEY>)
```

The sync job:
1. Fetches all coupons from Stripe
2. **Updates** existing local records: discount_type, discount_value, currency, max_uses, valid_till, is_active, reuse_policy
3. **Imports** Stripe coupons that don't exist locally yet
4. Updates `used_count = max(local, stripe.times_redeemed)`
5. Auto-deactivates locally (`is_active = False`) if `used_count >= max_uses`

**Sync response:**
```json
{
  "fetched": [{ "code": "SAVE10", "providers": ["stripe"] }],
  "imported": [{ "code": "NEWCODE", "from": "stripe" }],
  "errors":   [{ "provider": "stripe", "error": "connection refused" }],
  "auto_deactivated": [{ "code": "USED100", "used_count": 100, "max_uses": 100 }]
}
```

### 3. Admin optionally annotates the coupon

```
PATCH /v1/admin/coupons/{id}
{ "name": "Launch Week 20% Off", "description": "...", "reuse_policy": "single_use" }
```

- `name`, `description`, `reuse_policy`, `user_ids`, `is_active` — local metadata only, never pushed to PG
- `discount_type`, `discount_value`, `currency` — read-only (set by sync from PG)
- Running sync again after this PATCH will **not** overwrite name/description

### 4. User lists available coupons at checkout

```
GET /v1/coupons?provider=stripe
Authorization: Bearer <supabase-jwt>
```

Returns coupons that:
- `is_active = true`
- Not expired
- Not at global usage cap
- Either not targeted, or targeted to the requesting user
- Not already used by this user (if `reuse_policy = "single_use"`)
- Exist in Stripe (`stripe_synced_at IS NOT NULL`)

### 5. User validates a coupon before applying

```
POST /v1/coupons/validate
{ "code": "SAVE20", "amount": "1000.00", "currency": "INR" }
```

Returns:
```json
{
  "valid": true,
  "discount_type": "percentage",
  "discount_value": "20.00",
  "discount_amount": "200.00"
}
```

If invalid for any reason: `{ "valid": false }`. No error detail exposed.

### 6. Payment webhook increments used_count

When a payment succeeds, the PG sends a webhook to `POST /v1/payments`. The handler:
1. Increments `used_count` by 1
2. If `used_count >= max_uses`: sets `is_active = False` locally and logs a `CouponSyncIssue(auto_deactivated)` as an audit trail for admin

> **No API calls are made to Stripe from the webhook handler.** The coupon remains active in Stripe until deactivated there manually.

### 7. Admin checks sync status (single coupon)

```
POST /v1/admin/coupons/{id}/sync
```

Read-only diff — fetches current state from Stripe and compares. No changes made.

```json
{
  "stripe": { "in_sync": true, "mismatches": [] }
}
```

If a mismatch is found, update the value in the Stripe dashboard and run sync-all to pull the change.

### 8. Admin manages sync issues

**List pending issues:**
```
GET /v1/admin/coupons/sync-issues?status=pending
```

**Resolve or dismiss:**
```
PATCH /v1/admin/coupons/sync-issues/{issue_id}
{ "status": "dismissed", "resolved_by": "admin@example.com" }
```

---

## Provider Field Mapping

### Stripe → local

| Stripe field | Our field | Notes |
|---|---|---|
| `id` | `code` | Stripe coupon ID = our coupon code |
| `name` | import-time name only | Never overwritten after first import |
| `percent_off` | `discount_value` + `discount_type="percentage"` | |
| `amount_off` / 100 | `discount_value` + `discount_type="flat"` | Stripe stores paise (INR × 100) |
| `currency` | `currency` | For flat coupons |
| `max_redemptions` | `max_uses` | |
| `times_redeemed` | `used_count` reference | `used_count = max(local, times_redeemed)` |
| `deleted` | `is_active = false` | |
| `duration` | `reuse_policy` | `"once"` → `"single_use"`; `"repeating"` / `"forever"` → `"reusable"` |

---

## Configuration

| Env Var | Purpose |
|---|---|
| `STRIPE_API_KEY` | Stripe secret key (`sk_live_...` or `sk_test_...`). Leave empty to disable Stripe sync. |
| `STRIPE_API_URL` | Default: `https://api.stripe.com` |
| `WEBHOOK_API_KEY` | Bearer token for the cron endpoint `POST /v1/internal/coupons/sync` |

Stripe sync is opt-in. If credentials are not set, sync is silently skipped. Coupons created locally (via `POST /v1/admin/coupons`) still work without any PG configured.

---

## Known Limitations

### 1. `max_redemptions` is immutable post-creation in Stripe

Updating `max_uses` in our DB (via sync or PATCH) does not update Stripe's `max_redemptions`. Stripe will continue enforcing the original limit. To change it: deactivate the Stripe coupon and create a new one.

### 2. Stripe-originated flat discounts are in smallest currency unit

Stripe stores flat discount amounts in paise for INR (× 100). The sync converts these correctly: `amount_off / 100 = discount_value`. No action needed, but be aware when reading raw Stripe API responses.

### 3. Over-redemption window

Between a Stripe redemption event and the next webhook/sync reaching us, a near-limit coupon can be over-redeemed by concurrent requests. Stripe's own `max_redemptions` enforces a hard limit on the Stripe side. Our local limit provides an additional guard and audit trail. For critical limited coupons, use `user_ids` targeting.

---

## Admin Quick Reference

| Goal | Endpoint |
|---|---|
| Create a local coupon (no PG push) | `POST /v1/admin/coupons` |
| List all coupons | `GET /v1/admin/coupons` |
| Update metadata (name, reuse_policy, etc.) | `PATCH /v1/admin/coupons/{id}` |
| Deactivate locally | `DELETE /v1/admin/coupons/{id}` or `PATCH` with `is_active: false` |
| Assign to specific users | `POST /v1/admin/coupons/{id}/users` |
| Check sync diff vs Stripe | `POST /v1/admin/coupons/{id}/sync` |
| Pull all from Stripe (manual sync) | `POST /v1/admin/coupons/sync-all` |
| View sync issues | `GET /v1/admin/coupons/sync-issues?status=pending` |
| Dismiss an issue | `PATCH /v1/admin/coupons/sync-issues/{issue_id}` |
| Coupon statistics | `GET /v1/admin/coupons/stats` |
| User-facing coupon list (Stripe PG) | `GET /v1/coupons?provider=stripe` |
| Validate coupon at checkout | `POST /v1/coupons/validate` |
