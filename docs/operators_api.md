# Operators API Schema (Raw)

Source: live MCP call on February 15, 2026.

## Endpoint: `GET https://api.worldquantbrain.com/operators`

Top-level keys:
- `operators` (list)
- `count` (int)

Observed top-level response shape:

```json
{
  "operators": [
    {
      "name": "add",
      "category": "Arithmetic",
      "scope": ["REGULAR"],
      "definition": "add(x, y, filter = false), x + y",
      "description": "Adds two or more inputs element wise. Set filter=true to treat NaNs as 0 before summing.",
      "documentation": "/operators/add",
      "level": "ALL"
    },
    {
      "name": "abs",
      "category": "Arithmetic",
      "scope": ["REGULAR"],
      "definition": "abs(x)",
      "description": "Returns the absolute value of a number, removing any negative sign.",
      "documentation": "/operators/abs",
      "level": "ALL"
    },
    {
      "name": "to_nan",
      "category": "Arithmetic",
      "scope": ["REGULAR"],
      "definition": "to_nan(x, value=0, reverse=false)",
      "description": "Convert value to NaN or NaN to value if reverse=true",
      "documentation": null,
      "level": null
    },
    ...
  ],
  "count": 82
}
```

## Operator Item Schema

```json
{
  "name": "string",
  "category": "string",
  "scope": ["string", "..."],
  "definition": "string",
  "description": "string",
  "documentation": "string | null",
  "level": "string | null"
}
```

Notes:
- `documentation` can be `null` for some operators.
- `level` can be `null` for some operators.
- Current observed `scope` values are list form (for example `["REGULAR"]`).
