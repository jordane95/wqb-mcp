# User API Response Contracts

Source: `assets/logs/user_raw_probe.json` captured on February 15, 2026.

## GET https://api.worldquantbrain.com/users/self

```json
{
  "id": "ZL41483",
  "email": "zehan.li@qq.com",
  "telephone": "+8618801107595",
  "firstName": "Zehan",
  "lastName": "Li",
  "fullName": "LI ZEHAN",
  "gender": "MALE",
  "dateCreated": "2025-10-19T11:10:20-04:00",
  "dateVerified": "2025-10-19T11:10:59-04:00",
  "dateApproved": "2025-10-19T11:10:59-04:00",
  "verified": true,
  "approved": true,
  "address": {
    "street": null,
    "city": null,
    "state": null,
    "postalCode": null,
    "country": "CN"
  },
  "education": {
    "university": "Beihang University",
    "major": null,
    "degree": null,
    "stem": null,
    "graduationYear": null,
    "gpa": null,
    "maxGPA": null
  },
  "employment": null,
  "recruitment": null,
  "resume": null,
  "image": null,
  "settings": {
    "allowTracking": true,
    "communication": { "allowSMS": null },
    "privacy": {},
    "client": {}
  },
  "onboarding": { "status": "CONSULTANT_APPROVED" },
  "auxiliary": {
    "campaign": {
      "campaign": "Brain",
      "source": "Individual",
      "medium": "referral",
      "term": null,
      "content": null
    }
  },
  "geniusLevel": "GOLD"
}
```

## GET https://api.worldquantbrain.com/users/self/alphas?stage=OS&limit=20&offset=0

Uses the same alpha list response contract already documented in `docs/alpha_api.md`.

```json
{
  "count": 41,
  "next": "http://api.worldquantbrain.com:443/users/self/alphas?limit=20&offset=20&stage=OS",
  "previous": null,
  "results": [
    { "...": "Alpha details item (same shape as alpha_api.md)" },
    { "...": "..." }
  ]
}
```

## Shared Pagination Envelope

Used by `messages` and `activities`.

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

## GET https://api.worldquantbrain.com/users/self/messages?limit=10&offset=0

```json
{
  "count": 93,
  "next": "http://api.worldquantbrain.com:443/users/self/messages?limit=10&offset=10",
  "previous": null,
  "results": [
    {
      "id": "AP5MzdR",
      "type": "ANNOUNCEMENT",
      "title": "Research Paper: ...",
      "description": "<p>...</p>",
      "dateCreated": "2026-02-15T01:00:32.219668-05:00",
      "tags": [],
      "read": false
    }
  ]
}
```

## GET https://api.worldquantbrain.com/users/{user_id}/activities?grouping=day

```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    { "name": "base-payment", "title": "Base Payment" },
    { "name": "other-payment", "title": "Other Payment" },
    { "name": "referrals", "title": "Referrals" },
    { "name": "simulations", "title": "Simulated Alphas" },
    { "name": "submissions", "title": "Submitted Alphas" }
  ]
}
```

## GET https://api.worldquantbrain.com/users/self/activities/pyramid-multipliers

```json
{
  "pyramids": [
    {
      "category": { "id": "pv", "name": "Price Volume" },
      "region": "USA",
      "delay": 0,
      "multiplier": 1.6
    },
    {
      "category": { "id": "fundamental", "name": "Fundamental" },
      "region": "USA",
      "delay": 1,
      "multiplier": 1.2
    }
  ]
}
```

## GET https://api.worldquantbrain.com/users/self/activities/pyramid-alphas

```json
{
  "pyramids": [
    {
      "category": { "id": "pv", "name": "Price Volume" },
      "region": "USA",
      "delay": 0,
      "alphaCount": 0
    },
    {
      "category": { "id": "fundamental", "name": "Fundamental" },
      "region": "USA",
      "delay": 1,
      "alphaCount": 0
    }
  ]
}
```

## GET https://api.worldquantbrain.com/users/self/activities/base-payment

```json
{
  "yesterday": { "start": "2026-02-14", "end": "2026-02-14", "value": 0.0 },
  "current": { "start": "2026-01-01", "end": "2026-02-28", "value": 2.73 },
  "previous": { "start": "2025-11-01", "end": "2025-12-31", "value": 0.0 },
  "ytd": { "start": "2026-01-01", "end": "2026-02-14", "value": 2.73 },
  "total": { "start": "2025-12-25", "end": "2026-02-14", "value": 2.73 },
  "records": {
    "schema": {
      "name": "base-payment",
      "title": "Base Payment",
      "properties": [
        { "name": "date", "title": "Date", "type": "date" },
        { "name": "value", "title": "Base Payment", "type": "amount" }
      ]
    },
    "records": [
      ["2026-02-08", 1.37],
      ["2026-02-12", 1.36]
    ]
  },
  "currency": "USD",
  "type": "DAILY"
}
```

## GET https://api.worldquantbrain.com/users/self/activities/other-payment

```json
{
  "total": { "start": "2025-12-25", "end": "2026-02-14", "value": 0.0 },
  "records": {
    "schema": {
      "name": "other-payment",
      "title": "Other Payment",
      "properties": [
        { "name": "date", "title": "Date", "type": "date" },
        { "name": "value", "title": "Other Payment", "type": "amount" },
        { "name": "type", "title": "Type", "type": "text" }
      ]
    },
    "records": []
  },
  "currency": "USD",
  "type": "LIST"
}
```

## Computed Function: `value_factor_trendScore(start_date, end_date)`

This is a computed user-level function built from multiple API calls:
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
