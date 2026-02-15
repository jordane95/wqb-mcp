# Alpha Details Response Schema by Region

Endpoint: `GET https://api.worldquantbrain.com/alphas/{alpha_id}`

Source: `assets/alpha_region_details_raw.json` (captured February 15, 2026)  
Regions sampled: `USA`, `GLB`, `EUR`, `ASI`, `CHN`, `AMR`, `IND`

## Base Response Sample (Common Fields Only)

```json
{
  "id": "9qPmO8P1",
  "type": "REGULAR",
  "author": "ZL41483",
  "settings": {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "decay": 0,
    "neutralization": "SUBINDUSTRY",
    "truncation": 0.0,
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "OFF",
    "maxTrade": "OFF",
    "maxPosition": "OFF",
    "language": "FASTEXPR",
    "visualization": false,
    "startDate": "2014-01-01",
    "endDate": "2023-12-31"
  },
  "regular": {
    "code": "rank(close)",
    "description": null,
    "operatorCount": 1
  },
  "dateCreated": "2026-02-15T03:13:01-05:00",
  "dateSubmitted": null,
  "dateModified": "2026-02-15T03:13:01-05:00",
  "name": null,
  "favorite": false,
  "hidden": false,
  "color": null,
  "category": null,
  "tags": [],
  "classifications": [
    {
      "id": "DATA_USAGE:SINGLE_DATA_SET",
      "name": "Single Data Set Alpha"
    }
  ],
  "grade": null,
  "stage": "IS",
  "status": "UNSUBMITTED",
  "is": {
    "pnl": 1946403,
    "bookSize": 20000000,
    "longCount": 1528,
    "shortCount": 1533,
    "turnover": 0.0242,
    "returns": 0.0195,
    "drawdown": 0.5453,
    "margin": 0.001611,
    "sharpe": 0.19,
    "fitness": 0.08,
    "startDate": "2014-01-01",
    "investabilityConstrained": {
      "pnl": 2171661,
      "bookSize": 20000000,
      "longCount": 1512,
      "shortCount": 1618,
      "turnover": 0.0228,
      "returns": 0.0218,
      "drawdown": 0.5292,
      "margin": 0.001912,
      "fitness": 0.09,
      "sharpe": 0.21
    },
    "checks": [
      {
        "name": "LOW_SHARPE",
        "result": "FAIL",
        "limit": 1.58,
        "value": 0.19
      },
      {
        "name": "LOW_FITNESS",
        "result": "FAIL",
        "limit": 1.0,
        "value": 0.08
      },
      {
        "...": "region-specific check items continue"
      }
    ]
  },
  "os": null,
  "train": null,
  "test": null,
  "prod": null,
  "competitions": null,
  "themes": null,
  "pyramids": null,
  "pyramidThemes": null,
  "team": null,
  "osmosisPoints": null
}
```

## Region-Specific `is` Fields (Yes/No Matrix)

Additional fields are relative to the base `is` object shown above.
Legend: `+` present, `-` not present.

| Region | `glbAmer` | `glbApac` | `glbEmea` | `riskNeutralized` |
|---|---|---|---|---|
| `USA` | - | - | - | + |
| `GLB` | + | + | + | + |
| `EUR` | - | - | - | + |
| `ASI` | - | - | - | + |
| `CHN` | - | - | - | + |
| `AMR` | - | - | - | - |
| `IND` | - | - | - | + |

## Additional Field Schema

```json
{
  "glbAmer": {
    "pnl": 0.0,
    "bookSize": 0.0,
    "longCount": 0,
    "shortCount": 0,
    "turnover": 0.0,
    "returns": 0.0,
    "drawdown": 0.0,
    "margin": 0.0,
    "fitness": 0.0,
    "sharpe": 0.0
  },
  "glbApac": {
    "pnl": 0.0,
    "bookSize": 0.0,
    "longCount": 0,
    "shortCount": 0,
    "turnover": 0.0,
    "returns": 0.0,
    "drawdown": 0.0,
    "margin": 0.0,
    "fitness": 0.0,
    "sharpe": 0.0
  },
  "glbEmea": {
    "pnl": 0.0,
    "bookSize": 0.0,
    "longCount": 0,
    "shortCount": 0,
    "turnover": 0.0,
    "returns": 0.0,
    "drawdown": 0.0,
    "margin": 0.0,
    "fitness": 0.0,
    "sharpe": 0.0
  },
  "riskNeutralized": {
    "pnl": 0.0,
    "bookSize": 0.0,
    "longCount": 0,
    "shortCount": 0,
    "turnover": 0.0,
    "returns": 0.0,
    "drawdown": 0.0,
    "margin": 0.0,
    "fitness": 0.0,
    "sharpe": 0.0
  }
}
```

## `is.checks` Variant Design (6 Types)

### Variant: `simple`

```json
{
  "name": "CONCENTRATED_WEIGHT",
  "result": "PASS"
}
```

### Variant: `limit_value`

```json
{
  "name": "LOW_SHARPE",
  "result": "FAIL",
  "limit": 1.58,
  "value": 0.19
}
```

### Variant: `limit_value_ratio`

```json
{
  "name": "LOW_ROBUST_UNIVERSE_SHARPE.WITH_RATIO",
  "result": "FAIL",
  "ratio": 0.9,
  "limit": -0.06,
  "value": -0.23
}
```

### Variant: `competitions`

```json
{
  "name": "MATCHES_COMPETITION",
  "result": "PENDING",
  "competitions": [
    {
      "id": "AIACv2",
      "name": "AI Alphas Competition 2.0"
    }
  ]
}
```

### Variant: `pyramids`

```json
{
  "result": "PASS",
  "name": "MATCHES_PYRAMID",
  "effective": 1,
  "multiplier": 1.1,
  "pyramids": [
    {
      "name": "USA/D1/PV",
      "multiplier": 1.1
    }
  ]
}
```

### Variant: `themes`

```json
{
  "result": "WARNING",
  "name": "MATCHES_THEMES",
  "themes": [
    {
      "id": "EDrKL34",
      "multiplier": 2.0,
      "name": "JPN Dataset Utilization Theme"
    },
    {
      "id": "M4ZYx3D",
      "multiplier": 2.0,
      "name": "AMR Dataset Utilization Theme"
    }
  ]
}
```

## Computed Function: `value_factor_trendScore(start_date, end_date)`

This is a computed alpha-related function built from multiple API calls:
- `GET https://api.worldquantbrain.com/users/self/alphas` with `stage=OS` and submission date filters
- `GET https://api.worldquantbrain.com/alphas/{alpha_id}` for each regular alpha
- `GET https://api.worldquantbrain.com/users/self/activities/pyramid-multipliers` for `P_max`

Input:

```json
{
  "start_date": "2025-08-14T00:00:00Z",
  "end_date": "2025-08-18T23:59:59Z"
}
```

Output contract:

```json
{
  "diversity_score": 0.0123,
  "N": 40,
  "A": 10,
  "P": 5,
  "P_max": 12,
  "S_A": 0.25,
  "S_P": 0.4167,
  "S_H": 0.1184,
  "per_pyramid_counts": {
    "Value": 12,
    "Quality": 8,
    "Sentiment": 6,
    "Momentum": 9,
    "Volatility": 5
  }
}
```

Field meanings:
- `N`: total regular alphas in submission-date window.
- `A`: atom-like regular alphas.
- `P`: number of pyramids covered in sample.
- `P_max`: normalization denominator from pyramid multipliers (fallback `max(P, 1)`).
- `S_A`: atom ratio = `A / N` (0 if `N == 0`).
- `S_P`: pyramid coverage ratio = `P / P_max`.
- `S_H`: normalized entropy over `per_pyramid_counts` (0 when `P <= 1`).
- `diversity_score`: `S_A * S_P * S_H`.
