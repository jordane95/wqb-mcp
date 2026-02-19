# Correlation API Response Formats

Endpoint: `GET /alphas/{alpha_id}/correlations/{type}`

Types: `prod`, `self`, `power-pool`

Raw probe: `assets/logs/correlation_raw_probe.json`

## Polling

May return `200` with empty body and `Retry-After: 1.0` header when data is being computed.
Poll until a non-empty JSON body is returned.

## Common Structure

All three endpoints share the same top-level structure:

```json
{
  "schema": {
    "name": "string",
    "title": "string",
    "properties": [{"name": "string", "title": "string", "type": "string"}, ...]
  },
  "max": float | null,
  "min": float | null,
  "records": [[float | str | int | null, ...], ...]
}
```

- `schema`: describes the record format (column names, titles, types)
- `max` / `min`: aggregate max/min correlation values; `null` when no correlated alphas exist
- `records`: list of lists; empty `[]` when no correlated alphas exist

## Production Correlation

`GET /alphas/{alpha_id}/correlations/prod`

- `schema.name`: `"prodCorrelation"`
- Records are histogram buckets: 20 fixed bins from -1.0 to 1.0 in 0.1 steps
- Each record: `[bucket_low, bucket_high, alpha_count]`
- No individual alpha IDs are exposed

```json
{
  "schema": {
    "name": "prodCorrelation",
    "title": "Prod Correlated",
    "properties": [
      {"name": "min", "title": "Min", "type": "decimal"},
      {"name": "max", "title": "Max", "type": "decimal"},
      {"name": "alphas", "title": "№ Production Alphas", "type": "integer"}
    ]
  },
  "records": [
    [-1.0, -0.9, 0],
    [-0.9, -0.8, 0],
    ...
    [0.0,  0.1, 21468],
    ...
    [0.9,  1,   0]
  ],
  "max": 0.3343,
  "min": -0.1637
}
```

## Self / Power Pool Correlation

`GET /alphas/{alpha_id}/correlations/self`
`GET /alphas/{alpha_id}/correlations/power-pool`

Both use the same schema. `schema.name` is `"selfCorrelation"` for both.

Records are per-alpha detail rows with 11 fields:

```
index  name            type        example
0      id              string      "1YV8jJaR"
1      name            string      "MCP-submit-test" | null
2      instrumentType  string      "EQUITY"
3      region          string      "AMR"
4      universe        string      "TOP600"
5      correlation     decimal     0.5561
6      sharpe          decimal     1.2
7      returns         percent     0.0483
8      turnover        percent     0.0863
9      fitness         decimal     0.75
10     margin          permyriad   0.00112
```

Example (power-pool, 2 correlated alphas):

```json
{
  "schema": {"name": "selfCorrelation", "title": "Self Correlated", "properties": [...]},
  "records": [
    ["1YV8jJaR", "MCP-submit-test", "EQUITY", "AMR", "TOP600", 0.5561, 1.2, 0.0483, 0.0863, 0.75, 0.00112],
    ["3qYKVQWg", null,              "EQUITY", "AMR", "TOP600", 0.4087, 1.1, 0.0553, 0.0971, 0.73, 0.00114]
  ],
  "max": 0.5561,
  "min": 0.4087
}
```

Example (self, no correlated alphas):

```json
{
  "schema": {"name": "selfCorrelation", "title": "Self Correlated", "properties": [...]},
  "records": [],
  "max": null,
  "min": null
}
```

## Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 404 | `{"detail": "Not found."}` | Invalid alpha ID |

## Notes

- Remote `check_correlation` reads `record[0]` as alpha_id, `record[5]` as correlation — correct per schema
- `count` in remote code = `len(records)` — number of correlated alphas for self/power-pool
- For `prod`, `count` is always 20 (fixed histogram bins) — not meaningful as a count of correlated alphas
- `prod` only provides aggregate histogram; individual production alpha IDs are never exposed
- The `power-pool` endpoint works for both IS and OS alphas (returns cross-region PP correlations)

## Local Correlation

`check_local_correlation` computes self and power-pool correlation client-side using cached daily returns, without calling the remote `/correlations/` endpoints.

### How it works

1. **Sync baseline** — paginate `GET /users/self/alphas?stage=OS` to get all OS alphas, fetch their `daily-pnl` recordset data, and cache as parquet files
2. **Compute** — load cached returns into a single DataFrame, compute Pearson correlation of the candidate alpha against the baseline set
3. **Return** — produce the same `CorrelationData` / `CorrelationCheckResponse` models as the remote path

### Supported types

| Type | Supported | Notes |
|------|-----------|-------|
| `self` | Yes | Non-power-pool OS alphas in same region |
| `power-pool` | Yes | Power-pool OS alphas in same region |
| `prod` | No | Requires server-side data; raises `ValueError` |

### Cache layout

```
~/.wqb_mcp/alpha_cache/
├── index.json          # alpha metadata (region, stats, is_power_pool)
└── alphas/
    └── <alpha_id>/
        └── daily-pnl.parquet
```

### Batch mode

`batch_check_local_correlation` accepts a list of alpha IDs and returns:

- **`inter_correlation`** — each candidate vs the cached OS baseline (same as single check)
- **`intra_correlation`** — pairwise correlation matrix between the candidate alphas
