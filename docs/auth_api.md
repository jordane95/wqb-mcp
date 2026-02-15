# Authentication API Response Formats

Endpoints under `/authentication`.

Raw captures were collected on February 15, 2026.

## Common Success Body

Observed on both `POST /authentication` (login) and `GET /authentication` (session check):

```json
{
  "user": {
    "id": "string"
  },
  "token": {
    "expiry": 14400.0
  },
  "permissions": ["string", "..."]
}
```

- `user.id`: BRAIN user id (example: `"ZL41483"`)
- `token.expiry`: remaining token lifetime in seconds (float)
- `permissions`: granted capability list

## Login

`POST /authentication`

Request:

- Header `Authorization: Basic <base64(email:password)>`

Observed success:

- HTTP `201`
- `Content-Type: application/json`
- Response body follows Common Success Body
- Session auth cookie `t` is set

Observed sample:

```json
{
  "user": {"id": "ZL41483"},
  "token": {"expiry": 14400.0},
  "permissions": [
    "BEFORE_AND_AFTER_PERFORMANCE_V2",
    "BRAIN_LABS",
    "BRAIN_LABS_JUPYTER_LAB",
    "CONSULTANT",
    "MULTI_SIMULATION",
    "PROD_ALPHAS",
    "REFERRAL",
    "VISUALIZATION",
    "WORKDAY"
  ]
}
```

## Authentication Check

`GET /authentication` (after login/session cookie)

Observed success:

- HTTP `200`
- `Content-Type: application/json`
- Response body follows Common Success Body

Observed sample:

```json
{
  "user": {"id": "ZL41483"},
  "token": {"expiry": 14399.46177},
  "permissions": [
    "BEFORE_AND_AFTER_PERFORMANCE_V2",
    "BRAIN_LABS",
    "BRAIN_LABS_JUPYTER_LAB",
    "CONSULTANT",
    "MULTI_SIMULATION",
    "PROD_ALPHAS",
    "REFERRAL",
    "VISUALIZATION",
    "WORKDAY"
  ]
}
```

## Biometric Challenge Path

Code path in `client/auth.py` expects possible login challenge response:

- HTTP `401`
- Header `WWW-Authenticate: persona`
- Header `Location: <challenge_url>`

This `401 persona` response was not observed in the captured run above, but is handled by current client logic.
