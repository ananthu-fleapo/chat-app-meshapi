# Error Map — `/v1/templates`

> Source: `app/routers/templates.py`

Successful responses use the RouterV `TemplateSummary` schema.
All RouterV errors use the standard envelope:
```json
{"error": {"code": "<error_code>", "message": "..."}, "request_id": "req_..."}
```

**Exception:** HTTP 409 is raised via `HTTPException` directly (not `RouterVError`), so its body follows FastAPI's default format:
```json
{"detail": "A template named '...' already exists for owner '...'."}
```

---

## Error Table

### `POST /v1/templates` — Create

| HTTP | `error_code` | Circumstance | Category |
|---|---|---|---|
| 401 | `unauthorized` | Neither a valid Supabase JWT nor a valid `rsk_` API key in `Authorization` | Platform |
| 409 | _(FastAPI default format)_ | `IntegrityError` — `(name, owner)` unique constraint violation; a template with this name already exists for this owner | Platform |
| 500 | `internal_error` | Unhandled `SQLAlchemyError` during `db.flush()` that is **not** an `IntegrityError` (e.g. DB connection lost mid-write) | Platform |

---

### `GET /v1/templates` — List

| HTTP | `error_code` | Circumstance | Category |
|---|---|---|---|
| 401 | `unauthorized` | Invalid or missing credentials | Platform |
| 500 | `internal_error` | Unhandled `SQLAlchemyError` during the list query (`db.execute(select(Template)...)`) | Platform |

---

### `GET /v1/templates/{template_id}` — Get

| HTTP | `error_code` | Circumstance | Category |
|---|---|---|---|
| 401 | `unauthorized` | Invalid or missing credentials | Platform |
| 404 | `not_found` | `template_id` is not a valid UUID string | Platform |
| 404 | `not_found` | Template UUID not found in DB, or belongs to a different owner | Platform |
| 500 | `internal_error` | Unhandled `SQLAlchemyError` during `db.execute(select(Template)...)` | Platform |

---

### `PATCH /v1/templates/{template_id}` — Update

| HTTP | `error_code` | Circumstance | Category |
|---|---|---|---|
| 401 | `unauthorized` | Invalid or missing credentials | Platform |
| 404 | `not_found` | Template not found or not owned by caller | Platform |
| 409 | _(FastAPI default format)_ | `IntegrityError` — new `name` conflicts with an existing template for this owner | Platform |
| 500 | `internal_error` | Unhandled `SQLAlchemyError` during `db.flush()` that is not an `IntegrityError` | Platform |

---

### `DELETE /v1/templates/{template_id}` — Delete

| HTTP | `error_code` | Circumstance | Category |
|---|---|---|---|
| 401 | `unauthorized` | Invalid or missing credentials | Platform |
| 404 | `not_found` | Template not found or not owned by caller | Platform |
| 500 | `internal_error` | Unhandled `SQLAlchemyError` during `db.delete(template)` | Platform |

---

## Notes

- Auth on all template routes accepts **both** a Supabase JWT (dashboard session) and an `rsk_` data-plane key via `get_any_auth_owner()`.
- The 409 response does **not** follow the RouterV envelope — clients should handle both error shapes.
- Global templates (`owner = NULL`) are readable by all callers but cannot be modified via this API; `_get_own_or_404` filters by `Template.owner == owner`, so global templates always return 404 for write/delete operations.
