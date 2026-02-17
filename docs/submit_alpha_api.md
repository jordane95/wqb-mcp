# Submit Alpha API

Captured 2026-02-18 via `scripts/capture_submit_alpha_raw.py`.

## `POST /alphas/{alpha_id}/submit`

### 201 — Submission accepted (checks running)

- Status: `201 Created`
- Content-Type: `text/html; charset=UTF-8`
- Body: **empty** (Content-Length: 0)
- Key headers:
  - `Location`: `http://api.worldquantbrain.com:443/alphas/{alpha_id}/submit`
  - `Retry-After`: `1.0`

**Note:** Location uses `http://` but server requires `https://` — must fix scheme before polling.

### 403 — Rejection (checks resolved with failures)

- Status: `403 Forbidden`
- Content-Type: `application/json`
- Body: `{"is": {"checks": [...]}}` — full check results using standard `AlphaCheck` format
- Examples: `LOW_SHARPE FAIL`, `ALREADY_SUBMITTED FAIL`, `OLD_SIMULATION FAIL`

```json
{
  "is": {
    "checks": [
      { "name": "LOW_SHARPE", "result": "FAIL", "limit": 1.58, "value": 1.11 },
      { "name": "LOW_FITNESS", "result": "FAIL", "limit": 1.0, "value": 0.69 },
      { "name": "CONCENTRATED_WEIGHT", "result": "PASS" },
      { "name": "SELF_CORRELATION", "result": "PASS", "limit": 0.7 },
      { "name": "PROD_CORRELATION", "result": "PASS", "limit": 0.7, "value": 0.4705 }
    ]
  }
}
```

### 404 — Not found

- Status: `404 Not Found`
- Content-Type: `application/json`
- Body: `{"detail": "Not found."}`

## `GET /alphas/{alpha_id}/submit` (poll Location)

After a 201, poll the Location URL until checks resolve.

### 200 — Checks still running

- Status: `200 OK`
- Body: **empty**
- `Retry-After`: `1.0` (poll again after this delay)

### 403 — Checks resolved with failures (terminal)

- Status: `403 Forbidden`
- Body: same `{"is": {"checks": [...]}}` as POST 403
- `Retry-After`: absent

### 404 — Checks passed, alpha moved to OS (terminal success)

- Status: `404 Not Found`
- Body: empty
- `Retry-After`: absent
- The submit endpoint disappears once the alpha transitions to OS

### Observed flows

Failure (d58MKdn2):
```
POST /alphas/d58MKdn2/submit → 201 (Location + Retry-After: 1.0)
GET  .../submit → 200 (empty, Retry-After: 1.0)  ×11 polls
GET  .../submit → 403 (checks resolved, 3 FAIL)
```

Success (1YV8jJaR):
```
POST /alphas/1YV8jJaR/submit → 201 (Location + Retry-After: 1.0)
GET  .../submit → 200 (empty, Retry-After: 1.0)  ×13 polls
GET  .../submit → 404 (endpoint gone, alpha now OS/ACTIVE)
```

## Notes

- 201 means "checks are running async" — not "submission succeeded"
- Poll GET Location with Retry-After backoff until Retry-After disappears
- Terminal states: 404 (all checks passed, alpha → OS) or 403 (FAIL checks)
- Location header uses `http://` scheme but must be upgraded to `https://`
