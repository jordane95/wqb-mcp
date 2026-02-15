# Simulation API Schema (Raw)

Sources:
- `assets/logs/simulation_raw_probe.json` captured on February 15, 2026.
- `assets/logs/simulation_error_raw_probe.json` captured on February 15, 2026.
- `assets/logs/multi_simulation_raw_probe.json` captured on February 16, 2026.
- `assets/logs/multi_simulation_error_raw_probe.json` captured on February 16, 2026.

## Endpoint: `POST https://api.worldquantbrain.com/simulations`

Observed request shape (REGULAR):

```json
{
  "type": "REGULAR",
  "settings": {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "decay": 0.0,
    "neutralization": "NONE",
    "truncation": 0.0,
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "OFF",
    "language": "FASTEXPR",
    "visualization": false,
    "testPeriod": "P0Y0M",
    "maxTrade": "OFF"
  },
  "regular": "rank(close)"
}
```

Observed response:

- status code: `201`
- body: empty (`Content-Length: 0`, `text/html`)
- headers include:
  - `Location`: `https://api.worldquantbrain.com/simulations/{simulation_id}`
  - `Retry-After`: `"5.0"`

Representative response contract:

```json
{
  "status_code": 201,
  "body": null,
  "headers": {
    "Location": "https://api.worldquantbrain.com/simulations/{simulation_id}",
    "Retry-After": "5.0",
    "...": "..."
  }
}
```

## Endpoint: `GET https://api.worldquantbrain.com/simulations/{simulation_id}`

Observed in-progress response:

- status code: `200`
- header `Retry-After`: `"5.0"`
- body:

```json
{
  "progress": 0.1
}
```

Representative in-progress contract:

```json
{
  "progress": 0.1,
  "...": "..."
}
```

Headers:
- `Retry-After` is present while simulation is still running.

## Notes

- `POST /simulations` does not return a JSON body in this probe.
- The simulation tracking URL comes from `Location` header.
- Progress polling is performed via `GET /simulations/{simulation_id}`.

## Error Contracts

### Synchronous Validation Error (HTTP 400 on POST)

When settings/payload shape is invalid, `POST /simulations` returns `400` with field-keyed errors.

Representative contract:

```json
{
  "settings": {
    "region": ["\"XXX\" is not a valid choice."]
  }
}
```

Observed variants:

```json
{
  "settings": {
    "instrumentType": ["Instrument type CRYPTO is not available."],
    "region": ["Region USA is not available for instrument type CRYPTO."]
  }
}
```

```json
{
  "settings": {
    "delay": ["\"2\" is not a valid choice."]
  }
}
```

```json
{
  "settings": {
    "universe": ["\"TOP999999\" is not a valid choice."]
  }
}
```

```json
{
  "settings": {
    "region": ["This field is required."]
  }
}
```

```json
{
  "settings": {
    "errors": ["Invalid data. Expected a dictionary, but got str."]
  }
}
```

```json
{
  "regular": ["This field is required."]
}
```

### Asynchronous Expression Error (POST 201, then ERROR on polling)

For expression/semantic problems, `POST /simulations` can still return `201`, then polling later returns `status: "ERROR"`.

Representative contract from `GET /simulations/{simulation_id}`:

```json
{
  "id": "SSxjK91F5aMaS2F5j54VSB",
  "type": "REGULAR",
  "status": "ERROR",
  "message": "Attempted to use unknown variable \"this_field_does_not_exist_abc123\"",
  "location": {
    "line": 1,
    "start": 5,
    "end": 37,
    "property": "regular"
  }
}
```

Observed message variants:
- `Unexpected end of input`
- `Attempted to use unknown variable "..."`
- `Got invalid input at index 1, must be an expression`

## Client Error Handling Policy

For `create_simulation` (submit + single poll):

- If `POST /simulations` returns `>=400`, raise with:
  - endpoint (`/simulations`)
  - HTTP status code
  - parsed JSON error payload (or short body preview if non-JSON)
- If `POST /simulations` succeeds but `Location` header is missing, raise a structural error.
- On the first `GET /simulations/{simulation_id}` poll:
  - if HTTP status is `>=400`, raise with endpoint/status/payload
  - if body contains `{"status":"ERROR", ...}`, raise using `message` and `location`
  - otherwise return snapshot metadata (`retry_after`, `done`, and raw `snapshot`)

Recommended normalization for raised errors:

```json
{
  "stage": "submit | poll",
  "endpoint": "/simulations | /simulations/{id}",
  "status_code": 400,
  "detail": {}
}
```

## Client Response Schemas

### `create_simulation` (submit + one poll)

```json
{
  "simulation_id": "4aAc2ufOH58ibjPZCCLjrri",
  "location": "https://api.worldquantbrain.com/simulations/4aAc2ufOH58ibjPZCCLjrri",
  "retry_after": "5.0",
  "done": false,
  "snapshot": {
    "progress": 0.1
  }
}
```

Completed-on-first-poll variant:

```json
{
  "simulation_id": "4aAc2ufOH58ibjPZCCLjrri",
  "location": "https://api.worldquantbrain.com/simulations/4aAc2ufOH58ibjPZCCLjrri",
  "retry_after": null,
  "done": true,
  "snapshot": {
    "id": "4aAc2ufOH58ibjPZCCLjrri",
    "type": "REGULAR",
    "status": "COMPLETE",
    "alpha": "N1W8eLlL",
    "settings": {},
    "regular": "rank(close)"
  }
}
```

### `wait_for_simulation`

In-progress timeout/limit case:

```json
{
  "simulation_id": "4aAc2ufOH58ibjPZCCLjrri",
  "location": "https://api.worldquantbrain.com/simulations/4aAc2ufOH58ibjPZCCLjrri",
  "polls": 3,
  "done": false,
  "snapshot": {
    "progress": 0.35
  },
  "message": "Reached max_polls=3 before completion."
}
```

## Multi Simulation Contracts

### Endpoint: `POST https://api.worldquantbrain.com/simulations` (list payload)

Observed request shape:

```json
[
  {
    "type": "REGULAR",
    "settings": {
      "instrumentType": "EQUITY",
      "region": "USA",
      "universe": "TOP3000",
      "delay": 1,
      "decay": 0.0,
      "neutralization": "NONE",
      "truncation": 0.0,
      "pasteurization": "ON",
      "unitHandling": "VERIFY",
      "nanHandling": "OFF",
      "language": "FASTEXPR",
      "visualization": true,
      "testPeriod": "P0Y0M",
      "maxTrade": "OFF"
    },
    "regular": "rank(close)"
  },
  {
    "type": "REGULAR",
    "settings": { "...": "same settings" },
    "regular": "rank(open)"
  }
]
```

Observed response:
- status code: `201`
- body: empty
- header `Location`: `https://api.worldquantbrain.com/simulations/{multi_id}`

### Multi-Simulation With Per-Item Settings (one session)

Supported tool input shape:

```json
{
  "alpha_expressions": ["rank(close)", "rank(volume)"],
  "instrument_type": "EQUITY",
  "region": "USA",
  "delay": 1,
  "language": "FASTEXPR",
  "settings": [
    { "universe": "TOP200", "decay": 2.0 },
    { "universe": "TOP1000", "decay": 5.0 }
  ]
}
```

Rules:
- `settings` is optional; when present, it must have the same length as `alpha_expressions`.
- `settings[i]` is merged onto common top-level settings for `alpha_expressions[i]`.
- In one multi-simulation request, these keys must stay identical across all items:
  - `instrumentType`
  - `region`
  - `delay`
  - `language`

Allowed to differ per item (examples):
- `universe`
- `decay`
- `neutralization`
- `truncation`
- `testPeriod`
- `unitHandling`
- `nanHandling`
- `visualization`
- `pasteurization`
- `maxTrade`

### Endpoint: `GET https://api.worldquantbrain.com/simulations/{multi_id}`

Observed completion payload:

```json
{
  "children": [
    "1geG1O9AB4racB8NIicCZ20",
    "OKxLU4OR54L8G1qgcvTuLS"
  ],
  "type": "REGULAR",
  "settings": {
    "instrumentType": "EQUITY",
    "region": "USA",
    "delay": 1,
    "language": "FASTEXPR"
  },
  "status": "COMPLETE"
}
```

### Endpoint: `GET https://api.worldquantbrain.com/simulations/{child_id}`

Observed child completion payload:

```json
{
  "id": "1geG1O9AB4racB8NIicCZ20",
  "parent": "1ADcL76oj4ND9x01567SL67R",
  "type": "REGULAR",
  "settings": {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "decay": 0,
    "neutralization": "NONE",
    "truncation": 0.0,
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "OFF",
    "maxTrade": "OFF",
    "maxPosition": "OFF",
    "language": "FASTEXPR",
    "visualization": true
  },
  "regular": "rank(close)",
  "status": "COMPLETE",
  "alpha": "N1W8eLlL"
}
```

### Multi-Simulation Final Result Schema (tool/client target)

```json
{
  "multi_id": "1ADcL76oj4ND9x01567SL67R",
  "location": "https://api.worldquantbrain.com/simulations/1ADcL76oj4ND9x01567SL67R",
  "requested": 2,
  "children_total": 2,
  "children_completed": 2,
  "results": [
    {
      "child_id": "1geG1O9AB4racB8NIicCZ20",
      "status": "COMPLETE",
      "alpha_id": "N1W8eLlL"
    },
    {
      "child_id": "OKxLU4OR54L8G1qgcvTuLS",
      "status": "COMPLETE",
      "alpha_id": "pwJ3xOPV"
    }
  ]
}
```

### Multi-Simulation Error Contracts

#### Submit-time invalid settings (`POST /simulations` returns `400`)

For multi-simulation list payloads, the error payload is a **list** of per-item validation errors.

Representative contract:

```json
[
  {
    "settings": {
      "region": ["\"XXX\" is not a valid choice."]
    }
  },
  {
    "settings": {
      "region": ["\"XXX\" is not a valid choice."]
    }
  }
]
```

Observed variants:

```json
[
  { "settings": { "delay": ["\"2\" is not a valid choice."] } },
  { "settings": { "delay": ["\"2\" is not a valid choice."] } }
]
```

```json
[
  { "settings": { "universe": ["\"TOP999999\" is not a valid choice."] } },
  { "settings": { "universe": ["\"TOP999999\" is not a valid choice."] } }
]
```

```json
[
  {
    "settings": {
      "instrumentType": ["Instrument type CRYPTO is not available."],
      "region": ["Region USA is not available for instrument type CRYPTO."]
    }
  },
  {
    "settings": {
      "instrumentType": ["Instrument type CRYPTO is not available."],
      "region": ["Region USA is not available for instrument type CRYPTO."]
    }
  }
]
```

```json
[
  { "settings": { "region": ["This field is required."] } },
  { "settings": { "region": ["This field is required."] } }
]
```

Mixed valid + invalid settings item example:

Request (item 1 valid, item 2 invalid universe):

```json
[
  {
    "type": "REGULAR",
    "settings": {
      "instrumentType": "EQUITY",
      "region": "USA",
      "universe": "TOP1000",
      "delay": 1,
      "decay": 2.0,
      "neutralization": "NONE",
      "truncation": 0.0,
      "pasteurization": "ON",
      "unitHandling": "VERIFY",
      "nanHandling": "OFF",
      "language": "FASTEXPR",
      "visualization": true,
      "testPeriod": "P0Y0M",
      "maxTrade": "OFF"
    },
    "regular": "rank(close)"
  },
  {
    "type": "REGULAR",
    "settings": {
      "instrumentType": "EQUITY",
      "region": "USA",
      "universe": "NOT_A_UNIVERSE",
      "delay": 1,
      "decay": 5.0,
      "neutralization": "NONE",
      "truncation": 0.0,
      "pasteurization": "ON",
      "unitHandling": "VERIFY",
      "nanHandling": "OFF",
      "language": "FASTEXPR",
      "visualization": true,
      "testPeriod": "P0Y0M",
      "maxTrade": "OFF"
    },
    "regular": "rank(volume)"
  }
]
```

Observed `400` response payload:

```json
[
  {},
  {
    "settings": {
      "universe": ["\"NOT_A_UNIVERSE\" is not a valid choice."]
    }
  }
]
```

#### Mixed expressions (one valid, one invalid)

Observed behavior:
- submit succeeds (`201`)
- parent simulation ends with `status: "ERROR"`
- child simulations can have mixed terminal states

Parent terminal snapshot:

```json
{
  "children": [
    "3gPOsx7fQ5as8BYjKasl1Xu",
    "DztUebc85gAbtP1aihHEHNH"
  ],
  "type": "REGULAR",
  "status": "ERROR"
}
```

Child terminal snapshots:

```json
{
  "id": "3gPOsx7fQ5as8BYjKasl1Xu",
  "type": "REGULAR",
  "status": "CANCELLED"
}
```

```json
{
  "id": "DztUebc85gAbtP1aihHEHNH",
  "type": "REGULAR",
  "status": "ERROR",
  "message": "Attempted to use unknown variable \"this_field_does_not_exist_abc123\"",
  "location": {
    "line": 1,
    "start": 0,
    "end": 32,
    "property": "regular"
  }
}
```

Completion case:

```json
{
  "simulation_id": "4aAc2ufOH58ibjPZCCLjrri",
  "location": "https://api.worldquantbrain.com/simulations/4aAc2ufOH58ibjPZCCLjrri",
  "polls": 1,
  "done": true,
  "snapshot": {
    "id": "4aAc2ufOH58ibjPZCCLjrri",
    "type": "REGULAR",
    "status": "COMPLETE",
    "alpha": "N1W8eLlL"
  }
}
```
