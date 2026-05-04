# Zero Data Retention

When Zero Data Retention (ZDR) is enabled on your account, RouterV will never store the content of your requests or responses — your prompts and completions are processed and discarded immediately.

---

## What gets stored

| Data | ZDR off | ZDR on |
|---|---|---|
| Message content (prompts, completions) | Stored | Never stored |
| Token counts | Stored | Stored |
| Cost and billing | Stored | Stored |
| Model, latency, status code | Stored | Stored |

Billing and usage analytics are unaffected — you still see token counts, costs, and request counts in your dashboard. Only the message content itself is suppressed.

---

## Enabling ZDR

Toggle it in the dashboard under **Settings → Zero Data Retention**, or via the API:

```bash
curl -X PATCH https://api.routerv.com/v1/settings \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"zero_data_retention": true}'
```

```json
{ "zero_data_retention": true }
```

To disable:

```bash
curl -X PATCH https://api.routerv.com/v1/settings \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"zero_data_retention": false}'
```

### Check current status

```bash
curl https://api.routerv.com/v1/settings \
  -H "Authorization: Bearer <your-jwt>"
```

```json
{ "zero_data_retention": false }
```

---

## Propagation

Changes take effect within **5 minutes** for all API keys under your account. Requests in flight at the moment you toggle are unaffected — the new setting applies to requests logged after propagation.

---

## Notes

- ZDR applies to all API keys on your account. It cannot be set per-key.
- Existing logs are not retroactively deleted when you enable ZDR. Only new requests are affected.
- If you need existing logs removed, contact support.
