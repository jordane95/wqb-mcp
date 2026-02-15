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

## Additional Endpoints Probed (not used by client)

`GET https://api.worldquantbrain.com/users/self/pyramid/alphas` returned:

```json
{ "detail": "Not found." }
```

`GET https://api.worldquantbrain.com/activities/pyramid-alphas` returned:

```json
{ "detail": "Not found." }
```
