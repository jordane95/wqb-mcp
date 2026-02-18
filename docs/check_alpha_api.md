# Check Alpha API

Captured 2026-02-18 via `scripts/capture_check_alpha_raw.py`.

## `GET /alphas/{alpha_id}/check`

Platform's native submission-readiness check. Runs server-side checks (Sharpe, turnover, correlation, pyramid, themes, etc.) and returns results via Retry-After polling.

### 200 — Checks still running

- Status: `200 OK`
- Body: **empty** (Content-Length: 0)
- `Retry-After`: `1.0` (poll again after this delay)

### 200 — Checks complete

- Status: `200 OK`
- Content-Type: `application/json`
- `Retry-After`: absent
- Body: `{"is": {"checks": [...]}}` — full check results using standard `AlphaCheck` format

```json
{
  "is": {
    "checks": [
      { "name": "LOW_SHARPE", "result": "WARNING", "limit": 1.58, "value": 1.19 },
      { "name": "LOW_FITNESS", "result": "WARNING", "limit": 1.0, "value": 0.75 },
      { "name": "LOW_TURNOVER", "result": "PASS", "limit": 0.01, "value": 0.069 },
      { "name": "HIGH_TURNOVER", "result": "PASS", "limit": 0.7, "value": 0.069 },
      { "name": "CONCENTRATED_WEIGHT", "result": "PASS" },
      { "name": "LOW_SUB_UNIVERSE_SHARPE", "result": "PASS", "limit": 0.63, "value": 0.73 },
      { "name": "SELF_CORRELATION", "result": "PASS", "limit": 0.7 },
      { "name": "DATA_DIVERSITY", "result": "PASS" },
      { "name": "PROD_CORRELATION", "result": "PASS", "limit": 0.7, "value": 0.5019 },
      { "name": "REGULAR_SUBMISSION", "result": "PASS", "limit": 4, "value": 0 },
      { "name": "LOW_2Y_SHARPE", "result": "WARNING", "value": 0.83, "limit": 1.58 },
      { "name": "POWER_POOL_CORRELATION", "result": "PASS", "limit": 0.5, "value": 0.3321 },
      {
        "result": "PASS", "name": "MATCHES_PYRAMID",
        "effective": 1, "multiplier": 1.7,
        "pyramids": [{ "name": "AMR/D1/ANALYST", "multiplier": 1.7 }]
      },
      { "name": "OSMOSIS_ALLOCATION", "result": "WARNING" },
      {
        "result": "PASS", "name": "MATCHES_THEMES", "multiplier": 1.7,
        "themes": [
          { "id": "Zywp1YB", "multiplier": 1.0, "name": "OTHER/D1 Power Pool Feb`26 Theme" },
          { "id": "w402vB9", "multiplier": 1.7, "name": "AMR/D1/ANALYST Pyramid Theme" }
        ]
      },
      {
        "result": "WARNING", "name": "MATCHES_THEMES",
        "themes": [
          { "id": "JypwEj4", "multiplier": 2.0, "name": "EUR TOPCS1600 Theme" },
          { "id": "YynpodD", "multiplier": 1.0, "name": "EUR/D1 TOPCS1600 Power Pool Mar`26 Theme" }
        ]
      }
    ]
  }
}
```

### 200 — FAIL checks (e.g. QPrxWqE5)

Same structure, but with `result: "FAIL"` on failing checks:

```json
{
  "is": {
    "checks": [
      { "name": "LOW_SHARPE", "result": "FAIL", "limit": 1.58, "value": 1.16 },
      { "name": "LOW_FITNESS", "result": "FAIL", "limit": 1.0, "value": 0.71 },
      { "name": "LOW_2Y_SHARPE", "result": "FAIL", "value": -0.15, "limit": 1.58 },
      { "name": "POWER_POOL_CORRELATION", "result": "WARNING", "limit": 0.5, "value": 0.5561 }
    ]
  }
}
```

### 200 — Already submitted (OS alpha)

```json
{
  "is": {
    "checks": [
      { "name": "ALREADY_SUBMITTED", "result": "FAIL" }
    ]
  }
}
```

### 404 — Not found

- Status: `404 Not Found`
- Content-Type: `application/json`
- Body: `{"detail": "Not found."}`

## Check types observed

| name | result values | fields |
|------|--------------|--------|
| LOW_SHARPE | PASS/WARNING/FAIL | limit, value |
| LOW_FITNESS | PASS/WARNING/FAIL | limit, value |
| LOW_TURNOVER | PASS | limit, value |
| HIGH_TURNOVER | PASS | limit, value |
| CONCENTRATED_WEIGHT | PASS | (none) |
| LOW_SUB_UNIVERSE_SHARPE | PASS | limit, value |
| SELF_CORRELATION | PASS | limit |
| DATA_DIVERSITY | PASS | (none) |
| PROD_CORRELATION | PASS | limit, value |
| REGULAR_SUBMISSION | PASS | limit, value |
| LOW_2Y_SHARPE | WARNING/FAIL | limit, value |
| POWER_POOL_CORRELATION | PASS/WARNING | limit, value |
| MATCHES_PYRAMID | PASS | effective, multiplier, pyramids[] |
| OSMOSIS_ALLOCATION | WARNING | (none) |
| MATCHES_THEMES | PASS/WARNING | themes[], multiplier (optional) |
| ALREADY_SUBMITTED | FAIL | (none) |

## Notes

- Unlike `/submit`, this endpoint does NOT trigger submission — it only runs checks
- Polling pattern is identical to submit: 200 + Retry-After = still running, 200 without = done
- Response body uses the same `is.checks[]` format as submit 403 responses
- `MATCHES_THEMES` can appear multiple times (PASS for matched, WARNING for unmatched regions)
- `MATCHES_THEMES` has an optional top-level `multiplier` field (present when result=PASS)
