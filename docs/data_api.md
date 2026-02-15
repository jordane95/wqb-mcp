# Data API Schema (Raw)

Source: live MCP calls on February 15, 2026.

## Endpoint: `GET https://api.worldquantbrain.com/data-sets`

Tested params:
- `instrumentType=EQUITY`
- `region=USA`
- `delay=1`
- `universe=TOP3000`
- `theme=false`

Observed:
- `theme=ALL` returns `400 Bad Request`
- `theme=false` returns `200`

Top-level keys:
- `count` (int)
- `results` (list)

Representative response shape:

```json
{
  "count": 207,
  "results": [
    {
      "id": "analyst10",
      "name": "Performance-Weighted Analyst Estimates",
      "description": "...",
      "category": {"id": "analyst", "name": "Analyst"},
      "subcategory": {"id": "analyst-analyst-estimates", "name": "Analyst Estimates"},
      "region": "USA",
      "delay": 1,
      "universe": "TOP3000",
      "dateCoverage": 1.0,
      "coverage": 0.8405,
      "valueScore": 3.0,
      "userCount": 750,
      "alphaCount": 2389,
      "fieldCount": 1074,
      "pyramidMultiplier": 1.2,
      "themes": [],
      "researchPapers": [
        {
          "type": "discussion",
          "title": "Getting started with Analyst Datasets",
          "url": "https://support.worldquantbrain.com/..."
        }
      ]
    },
    ...
  ]
}
```

## Endpoint: `GET https://api.worldquantbrain.com/data-fields`

Tested params:
- `instrumentType=EQUITY`
- `region=USA`
- `delay=1`
- `universe=TOP3000`
- `type=MATRIX`
- `search=close`

Top-level keys:
- `count` (int)
- `results` (list)

Representative response shape:

```json
{
  "count": 689,
  "results": [
    {
      "id": "close",
      "description": "Daily close price",
      "dataset": {"id": "pv1", "name": "Price Volume Data for Equity"},
      "category": {"id": "pv", "name": "Price Volume"},
      "subcategory": {"id": "pv-price-volume", "name": "Price Volume"},
      "region": "USA",
      "delay": 1,
      "universe": "TOP3000",
      "type": "MATRIX",
      "dateCoverage": 1.0,
      "coverage": 1.0,
      "userCount": 37418,
      "alphaCount": 465837,
      "pyramidMultiplier": 1.1,
      "themes": []
    },
    ...
  ]
}
```

## Shared Structure

Both endpoints return:
- `count`
- `results` list
- items with nested objects (`category`, and for data-fields also `dataset`)
- numeric coverage/activity metrics
- `themes` as list

## Notable Differences

- `data-sets` items include `fieldCount` and optional `researchPapers`.
- `data-fields` items include `dataset` and field-level metadata (`type`).
