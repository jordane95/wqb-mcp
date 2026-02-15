# Alpha Recordsets API

Source sample: `assets/alpha_recordsets_raw_kqk3X0bL.json`  
Alpha: `kqk3X0bL` (`GLB`)  
Last validated: February 15, 2026

## Endpoint

`GET https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/{record_set_name}`

Allowed `record_set_name` values (fixed enum):
- `pnl`
- `sharpe`
- `turnover`
- `daily-pnl`
- `yearly-stats`

## Raw Response Contract

Top-level keys:
- `schema`
- `records`

```json
{
  "schema": {
    "name": "pnl",
    "title": "PnL",
    "properties": [
      {"name": "date", "title": "Date", "type": "date"},
      {"name": "pnl", "title": "PnL", "type": "amount"}
    ]
  },
  "records": [
    ["2014-01-01", 0.0],
    ["2014-01-02", 0.0]
  ]
}
```

Notes:
- `records` is kept raw as list-of-lists.
- Column names/order are defined by `schema.properties`.
- `schema.name` is enum-validated in client code.

## Client Model

File: `src/wqb_mcp/client/alpha_recordsets.py`

Model:
- `AlphaRecordSetResponse`
  - `schema_` (`alias="schema"`) -> `RecordSetSchema`
  - `records` -> `List[List[Union[str, int, float, None]]]`

Helpers on `AlphaRecordSetResponse`:
- `rows_as_dicts()`: converts rows using `schema.properties[*].name`
- `save_csv(path)`: writes CSV header from schema, then raw rows

## MCP Tool Behavior

Tool: `get_record_set_data` in `src/wqb_mcp/tools/alpha_tools.py`

Inputs:
- `alpha_id`
- `record_set_name` (literal fixed set above)
- `output_path` (optional)

Behavior:
- fetches raw recordset JSON
- saves to CSV
  - default path: `assets/recordsets/{alpha_id}_{record_set_name_with_underscores}.csv`
- returns markdown summary (not the full payload), including:
  - alpha id
  - recordset name
  - saved path
  - row count
  - column count
  - headers

## Auth/Session Troubleshooting

Observed failure mode (before re-authentication):
- status `200`
- `Content-Type: text/html; charset=UTF-8`
- empty body
- JSON parse error: `Non-JSON response ...`

This indicates the API call did not return the expected JSON payload (commonly stale/invalid session).  
Resolution: call `authenticate` first, then retry `get_record_set_data`.

## Recordset Notes

`pnl` vs `daily-pnl`:
- `daily-pnl` is day increment style.
- `pnl` behaves as cumulative curve level.
- In sample data, `daily-pnl[t]` is close to `pnl[t] - pnl[t-1]` (minor rounding differences possible).
