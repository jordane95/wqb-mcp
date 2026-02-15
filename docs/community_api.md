# Community API Schema (Raw)

Source: `assets/logs/community_raw_probe.json` captured on February 15, 2026.

## Endpoint: `GET https://api.worldquantbrain.com/events`

Top-level keys:
- `count` (int)
- `next` (null | string)
- `previous` (null | string)
- `results` (list)

Representative response shape:

```json
{
  "count": 4,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "ZOEPXZN",
      "title": "Opportunity webinar - November 2025",
      "type": "ONLINE",
      "category": null,
      "start": "2025-11-11T08:00:00-05:00",
      "end": "2025-11-11T09:00:00-05:00",
      "timezone": "US/Eastern",
      "language": "en",
      "description": "...",
      "register": "https://worldquant.zoom.us/...",
      "venue": null,
      "city": null,
      "country": ""
    },
    ...
  ]
}
```

## Endpoint: `GET https://api.worldquantbrain.com/consultant/boards/leader?user={user_id}`

Top-level keys:
- `count` (int)
- `next` (null | string)
- `previous` (null | string)
- `results` (list)

Representative response shape:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "user": "ZL41483",
      "weightFactor": 0,
      "valueFactor": 0.5,
      "dailyOsmosisRank": 0.0,
      "dataFieldsUsed": 5,
      "submissionsCount": 2,
      "meanProdCorrelation": 0.8012,
      "meanSelfCorrelation": 0.0,
      "superAlphaSubmissionsCount": 0,
      "superAlphaMeanProdCorrelation": 0.0,
      "superAlphaMeanSelfCorrelation": 0.0,
      "university": "Beihang University",
      "country": "CN"
    }
  ]
}
```

## Endpoint: `GET https://api.worldquantbrain.com/users/{user_id}/competitions`

Top-level keys:
- `count` (int)
- `next` (null | string)
- `previous` (null | string)
- `results` (list)

Representative response shape:

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "AIACv2",
      "name": "AI Alphas Competition 2.0",
      "description": "AI Alphas Competition 2.0",
      "universities": null,
      "countries": null,
      "excludedCountries": null,
      "status": "ACCEPTED",
      "teamBased": false,
      "startDate": "2026-01-19T00:00:00-05:00",
      "endDate": "2026-02-15T23:59:59-05:00",
      "signUpStartDate": "2026-01-19T00:00:00-05:00",
      "signUpEndDate": "2026-02-08T23:59:59-05:00",
      "signUpDate": "2026-01-19T00:00:00-05:00",
      "team": null,
      "scoring": "PERFORMANCE",
      "leaderboard": {
        "rank": 10125,
        "user": "ZL41483",
        "alphas": 0,
        "score": 0.0,
        "notebookSubmission": 0,
        "presentationSubmission": 0,
        "university": "Beihang University",
        "country": "CN"
      },
      "prizeBoard": false,
      "universityBoard": false,
      "submissions": true,
      "faq": "https://support.worldquantbrain.com/...",
      "progress": null
    },
    ...
  ]
}
```

## Endpoint: `GET https://api.worldquantbrain.com/competitions/{competition_id}`

Representative response shape:

```json
{
  "id": "AIACv2",
  "name": "AI Alphas Competition 2.0",
  "description": "AI Alphas Competition 2.0",
  "universities": null,
  "countries": null,
  "excludedCountries": null,
  "status": "ACCEPTED",
  "teamBased": false,
  "startDate": "2026-01-19T00:00:00-05:00",
  "endDate": "2026-02-15T23:59:59-05:00",
  "signUpStartDate": "2026-01-19T00:00:00-05:00",
  "signUpEndDate": "2026-02-08T23:59:59-05:00",
  "signUpDate": "2026-01-19T00:00:00-05:00",
  "team": null,
  "scoring": "PERFORMANCE",
  "leaderboard": {
    "rank": 10125,
    "user": "ZL41483",
    "alphas": 0,
    "score": 0.0,
    "notebookSubmission": 0,
    "presentationSubmission": 0,
    "university": "Beihang University",
    "country": "CN"
  },
  "prizeBoard": false,
  "universityBoard": false,
  "submissions": true,
  "faq": "https://support.worldquantbrain.com/...",
  "progress": null
}
```

## Endpoint: `GET https://api.worldquantbrain.com/competitions/{competition_id}/agreement`

Representative response shape:

```json
{
  "id": "aiacv2-agreement",
  "title": "AI Alphas Competition 2.0",
  "lastModified": "2026-01-18T22:56:54.205384-05:00",
  "content": [
    {
      "type": "TEXT",
      "value": "<ol><li>...</li></ol><p>...</p>",
      "id": "e8ca7c30-4425-4c8f-b352-08801871249e"
    }
  ]
}
```

## Endpoint: `GET https://api.worldquantbrain.com/tutorials`

Top-level keys:
- `count` (int)
- `next` (null | string)
- `previous` (null | string)
- `results` (list)

Representative response shape:

```json
{
  "count": 11,
  "next": "http://api.worldquantbrain.com:443/tutorials?limit=10&offset=10",
  "previous": null,
  "results": [
    {
      "id": "discover-brain",
      "category": "Getting Started",
      "pages": [
        {
          "title": "*Read this First * - Starter Pack",
          "id": "read-first-starter-pack",
          "lastModified": "2025-04-24T02:12:04.820122-04:00"
        }
      ],
      "title": "Discover BRAIN",
      "sequence": 0,
      "lastModified": "2023-03-30T10:03:04.259135-04:00"
    }
  ]
}
```

## Endpoint: `GET https://api.worldquantbrain.com/tutorial-pages/{page_id}`

Representative response shape:

```json
{
  "id": "read-first-starter-pack",
  "title": "*Read this First * - Starter Pack",
  "lastModified": "2025-04-24T02:12:04.820122-04:00",
  "content": [
    {
      "type": "TEXT",
      "value": "<p>...</p>",
      "id": "fddd633b-93d0-4faf-a316-14fe69dce7ce"
    },
    {
      "type": "HEADING",
      "value": { "level": "1", "content": "Research Consultant" },
      "id": "f113c3b6-23e6-4f20-82eb-37473fe92de7"
    },
    {
      "type": "IMAGE",
      "value": {
        "title": "consultant_1.jpg",
        "width": 451,
        "height": 291,
        "fileSize": 45439,
        "url": "https://api.worldquantbrain.com/content/images/.../consultant_1.jpg"
      },
      "id": "4fd33025-c8d5-434e-a5c5-22bf89573692"
    }
  ],
  "sequence": 0,
  "category": "Getting Started"
}
```

## Auxiliary Endpoint Used by Client: `GET https://api.worldquantbrain.com/users/self`

Used to derive `user_id` for leaderboard and user competitions when not provided.

Representative response shape:

```json
{
  "id": "ZL41483",
  "email": "zehan.li@qq.com",
  "fullName": "LI ZEHAN",
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
  "settings": {
    "allowTracking": true,
    "communication": {"allowSMS": null},
    "privacy": {},
    "client": {}
  },
  "onboarding": {"status": "CONSULTANT_APPROVED"},
  "geniusLevel": "GOLD"
}
```
