# Forum API (Playwright-based)

The forum tools scrape the WorldQuant BRAIN support site (`support.worldquantbrain.com`) using Playwright. They are **not REST API calls** — they use browser automation with session transfer from the BRAIN API client.

Source: `src/wqb_mcp/forum.py`
Captured: February 16, 2026

## Authentication Flow

1. Authenticate via BRAIN API (`brain_client.authenticate`)
2. Transfer session cookies to a headless Chromium browser context
3. Navigate to support site pages as an authenticated user

## Endpoints

### Glossary Terms

**URL**: `https://support.worldquantbrain.com/hc/en-us/articles/4902349883927`

Parses the glossary article HTML to extract term/definition pairs.

Response model: `GlossaryResponse`

```json
{
  "terms": [
    {"term": "Alpha", "definition": "An Alpha is defined by WorldQuant as..."},
    {"term": "Sharpe ratio", "definition": "This is a common mathematical ratio..."}
  ]
}
```

Parsing heuristics:
- Lines < 80 chars starting with uppercase → treated as terms
- Following lines until next term → definition
- Filters out navigation, metadata, and short definitions (< 10 chars)

### Search Forum Posts

**URL**: `https://support.worldquantbrain.com/hc/{locale}/search?page={n}&query={query}`

Default locale: `zh-cn`. Paginates through search results.

Response model: `ForumSearchResponse`

```json
{
  "results": [
    {
      "title": "SHARPE",
      "link": "https://support.worldquantbrain.com/hc/...",
      "snippet": "夏普比率...",
      "votes": 0,
      "comments": 0,
      "author": "YZ42460",
      "date": "2023-08-21T13:55:13Z",
      "breadcrumbs": ["WorldQuantBrain-CN", "社区", "中文论坛"]
    }
  ],
  "total_found": 3
}
```

### Read Forum Post

**URL**: `https://support.worldquantbrain.com/hc/zh-cn/community/posts/{article_id}`

Reads full post content and optionally paginates through all comments.

Response model: `ForumPostResponse`

```json
{
  "post": {
    "title": "SHARPE",
    "author": "YZ42460",
    "body": "Sharpe: Average measure of risk-adjusted returns...",
    "details": {
      "votes": "0",
      "date": "2年前"
    }
  },
  "comments": [
    {
      "author": "XX12345",
      "body": "Great explanation...",
      "date": "1年前"
    }
  ],
  "total_comments": 1
}
```

## Notes

- Forum tools are slower than API tools due to Playwright browser startup
- Requires Chromium to be installed (`playwright install chromium`)
- Comments are deduplicated across pagination pages
- Post body is truncated to 2000 chars in `__str__` output; comments to 300 chars each, max 5 shown
