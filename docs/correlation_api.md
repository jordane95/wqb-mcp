# Correlation API Response Formats

Endpoints under `/alphas/{alpha_id}/correlations/`.

## Common Structure

All three endpoints (prod, self, power-pool) share the same top-level structure:

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
- `max` / `min`: aggregate max/min correlation values, can be `null`
- `records`: list of lists, where each inner list's values can be `float`, `str`, `int`, or `null`

## Production Correlation

`GET /alphas/{alpha_id}/correlations/prod`

- `schema.name`: `"prodCorrelation"`
- Records are histogram buckets: `[bucket_low, bucket_high, count]`

```json
{
  "schema": {
    "name": "prodCorrelation",
    "title": "Prod Correlated",
    "properties": [
      {"name": "min", "title": "Min", "type": "decimal"},
      {"name": "max", "title": "Max", "type": "decimal"},
      {"name": "alphas", "title": "# Production Alphas", "type": "integer"}
    ]
  },
  "max": 0.7236,
  "min": -0.4575,
  "records": [
    [-1.0, -0.9, 0],
    [-0.9, -0.8, 0]
  ]
}
```

## Self Correlation

`GET /alphas/{alpha_id}/correlations/self`

- `schema.name`: `"selfCorrelation"`
- Records are per-alpha details: `[id, name, instrumentType, region, universe, correlation, sharpe, returns, turnover, fitness, margin]`
- `max`/`min` can be `null` when no correlated alphas exist

```json
{
  "schema": {
    "name": "selfCorrelation",
    "title": "Self Correlated",
    "properties": [
      {"name": "id", "title": "Id", "type": "string"},
      {"name": "name", "title": "Name", "type": "string"},
      {"name": "instrumentType", "title": "Instrument Type", "type": "string"},
      {"name": "region", "title": "Region", "type": "string"},
      {"name": "universe", "title": "Universe", "type": "string"},
      {"name": "correlation", "title": "Correlation", "type": "decimal"},
      {"name": "sharpe", "title": "Sharpe", "type": "decimal"},
      {"name": "returns", "title": "Returns", "type": "percent"},
      {"name": "turnover", "title": "Turnover", "type": "percent"},
      {"name": "fitness", "title": "Fitness", "type": "decimal"},
      {"name": "margin", "title": "Margin", "type": "permyriad"}
    ]
  },
  "max": 0.85,
  "min": -0.12,
  "records": [
    ["alphaId1", "name1", "EQUITY", "USA", "TOP3000", 0.85, 1.27, 0.0892, 0.5522, 0.51, 0.000323]
  ]
}
```

## Power Pool Correlation

`GET /alphas/{alpha_id}/correlations/power-pool`

Same schema and record format as Self Correlation (`schema.name` is also `"selfCorrelation"`).
