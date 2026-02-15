# Simulation API Schema (Raw)

Sources:
- `assets/logs/simulation_raw_probe.json` captured on February 15, 2026.
- `assets/logs/simulation_error_raw_probe.json` captured on February 15, 2026.

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
