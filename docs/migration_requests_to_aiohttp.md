# Migration Plan: `requests.Session` → `aiohttp.ClientSession`

## Context

The `BrainApiClient` declares all methods as `async def` but uses sync `requests.Session` for HTTP — making the async meaningless. `time.sleep()` blocks the event loop, parallel I/O is impossible, and sync scripts had to duplicate HTTP logic because the "async" client couldn't be reused.

This migration replaces `requests.Session` with `aiohttp.ClientSession` so the client is genuinely async.

## API Differences Cheat Sheet

| Feature | `requests` (current) | `aiohttp` (target) |
|---|---|---|
| GET/POST | `session.get(url)` → `Response` | `await session.get(url)` → `ClientResponse` |
| JSON body | `response.json()` (sync) | `await response.json()` (async) |
| Text body | `response.text` (property) | `await response.text()` (async method) |
| Status code | `response.status_code` | `response.status` |
| Headers | `response.headers` (dict-like) | `response.headers` (CIMultiDictProxy) — same API |
| raise_for_status | `response.raise_for_status()` | `response.raise_for_status()` — same |
| URL | `response.url` (str) | `response.url` (yarl.URL, use `str(response.url)`) |
| Cookies get | `session.cookies.get('t')` | `session.cookie_jar.filter_cookies(url).get('t')` |
| Cookies clear | `session.cookies.clear()` | `session.cookie_jar.clear()` |
| Timeout | `session.timeout = 30` | `aiohttp.ClientTimeout(total=30)` |
| Auth | `session.auth = None` | No equivalent attr; pass `auth=` per-request |
| POST json | `session.post(url, json=data)` | `await session.post(url, json=data)` |
| PATCH json | `session.patch(url, json=data)` | `await session.patch(url, json=data)` |
| OPTIONS | `session.options(url)` | `await session.options(url)` |
| Session headers | `session.headers.update({...})` | `ClientSession(headers={...})` at creation |

---

## Change Order (Dependency-Aware)

```
Phase 0: pyproject.toml (add aiohttp dep)
Phase 1: utils.py (make parse_json_or_error async-compatible)
Phase 2: client/__init__.py (swap session creation)
Phase 3: client/auth.py (cookie jar + response API changes)
Phase 4: All other mixins (mechanical transform)
Phase 5: client/user.py _get_json helper (sync→async)
Phase 6: forum.py (cookie transfer adaptation)
Phase 7: Verification
```

---

## Phase 0: `pyproject.toml`

**File**: `pyproject.toml`

**Changes**:
```toml
dependencies = [
    "mcp",
    "aiohttp",          # ADD
    "playwright",
    "beautifulsoup4",
    "pandas",
    "tabulate",
    "requests",          # KEEP — used by forum.py
    "pydantic",
    "keyring",
]
```

`requests` stays because `forum.py` uses it directly.

---

## Phase 1: `utils.py` — Make `parse_json_or_error` async-compatible

**File**: `src/wqb_mcp/utils.py`

**Problem**: `parse_json_or_error` calls `response.json()` (sync in requests) and reads `response.text` (property in requests). In aiohttp, both are async. But this function is also used in `_raise_http_error_with_payload` which is a `@staticmethod`.

**Solution**: Change `parse_json_or_error` to accept pre-parsed data. All call sites will `await response.json()` first, then pass the dict. This avoids making the utility async and keeps it simple.

**New signature**:
```python
async def parse_json_or_error(response: aiohttp.ClientResponse, endpoint: str) -> Any:
    """Parse JSON payload or raise a detailed parsing error."""
    try:
        return await response.json()
    except Exception as e:
        text = await response.text()
        preview = (text or "")[:200]
        ct = response.headers.get("Content-Type")
        raise ValueError(
            f"Non-JSON response from {endpoint} | status={response.status} | "
            f"content-type={ct} | body={preview!r} | error={e}"
        ) from e
```

**Key changes**:
- `def` → `async def`
- `response.json()` → `await response.json()`
- `response.text` → `await response.text()`
- `response.status_code` → `response.status`

**Impact**: Every call site that does `parse_json_or_error(response, endpoint)` must become `await parse_json_or_error(response, endpoint)`. All call sites are already inside `async def` methods, so this is safe.

**Exception**: `_raise_http_error_with_payload` in `simulation.py` is a `@staticmethod`. It must become `async` too (and callers must `await` it).

---

## Phase 2: `client/__init__.py` — Session Swap

**File**: `src/wqb_mcp/client/__init__.py`

**Changes**:
```python
import aiohttp
# Remove: import requests

class BrainApiClient(...):
    def __init__(self):
        self.base_url = "https://api.worldquantbrain.com"
        self.session: aiohttp.ClientSession | None = None
        self.auth_credentials = None
        self.is_authenticating = False
        self._default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self._timeout = aiohttp.ClientTimeout(total=30)

    async def _ensure_session(self):
        """Lazily create aiohttp.ClientSession (must be created inside async context)."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self._default_headers,
                timeout=self._timeout,
                cookie_jar=aiohttp.CookieJar(unsafe=True),  # unsafe=True allows non-HTTPS cookies
            )

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
```

**Why lazy creation**: `aiohttp.ClientSession` must be created inside a running event loop. The module-level `brain_client = BrainApiClient()` runs at import time (no event loop). So session creation is deferred to first use.

**Why `unsafe=True`**: The BRAIN API sets cookies on `api.worldquantbrain.com`. Without `unsafe=True`, aiohttp's cookie jar may reject cookies from non-HTTPS responses during redirects.

**Singleton pattern**: Keep `brain_client = BrainApiClient()` at module level. The session is created lazily on first API call.

---

## Phase 3: `client/auth.py` — Cookie Jar + Response API

**File**: `src/wqb_mcp/client/auth.py`

This is the most complex mixin because it directly manipulates cookies and handles multiple response status codes.

**Changes**:

### 3.1 `authenticate()`
```python
async def authenticate(self, email: str, password: str) -> AuthResponse:
    await self._ensure_session()

    # Clear cookies
    self.session.cookie_jar.clear()
    # No self.session.auth = None needed (aiohttp has no session-level auth)

    credentials = f"{email}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {'Authorization': f'Basic {encoded_credentials}'}

    try:
        async with self.session.post(
            'https://api.worldquantbrain.com/authentication',
            headers=headers
        ) as response:
            status = response.status  # was: response.status_code
            response_headers = response.headers
            response_url = str(response.url)  # was: response.url (str)

            if status == 201:
                self.log("Authentication successful", "SUCCESS")
                # Cookie 't' is auto-stored in cookie_jar
                jwt_token = self._get_cookie('t')
                ...
                parsed = await parse_json_or_error(response, "/authentication")
                self.auth_credentials = {'email': email, 'password': password}
                return AuthResponse.model_validate(parsed)

            if status == 401:
                www_auth = response_headers.get("WWW-Authenticate")
                location = response_headers.get("Location")
                if www_auth == "persona":
                    if not location:
                        raise AuthChallengeRequired(...)
                    from urllib.parse import urljoin
                    biometric_url = urljoin(response_url, location)
                    return await self._handle_biometric_auth(biometric_url, email, password)
                raise AuthInvalidCredentials(...)

            if status == 429:
                retry_after = response_headers.get("Retry-After")
                ...

            raise AuthError(f"Authentication failed with status code: {status}")
    except aiohttp.ClientError as e:
        raise AuthTransportError(f"Authentication request failed: {e}") from e
```

**Critical pattern**: aiohttp responses must be consumed inside `async with` context manager. The response body is only available within the `async with` block. All `response.json()`, `response.text()`, `response.headers`, `response.status` must be accessed before exiting the block.

### 3.2 Cookie helper method (add to `AuthMixin` or `BrainApiClient`)
```python
def _get_cookie(self, name: str) -> str | None:
    """Get a cookie value from the session cookie jar."""
    from yarl import URL
    for cookie in self.session.cookie_jar:
        if cookie.key == name:
            return cookie.value
    return None
```

### 3.3 `is_authenticated()`
```python
async def is_authenticated(self) -> bool:
    await self._ensure_session()
    jwt_token = self._get_cookie('t')
    if not jwt_token:
        return False
    try:
        async with self.session.get(f"{self.base_url}/authentication") as response:
            if response.status == 200:
                return True
            elif response.status == 401:
                return False
            else:
                return False
    except Exception as e:
        self.log(f"Error checking authentication: {str(e)}", "ERROR")
        return False
```

### 3.4 `_handle_biometric_auth()`
Same pattern: `self.session.post(biometric_url)` → `async with self.session.post(biometric_url) as check_response:`, read status/json inside the block.

### 3.5 `get_authentication_status()`
```python
async def get_authentication_status(self):
    await self._ensure_session()
    async with self.session.get(f"{self.base_url}/users/self") as response:
        response.raise_for_status()
        return await parse_json_or_error(response, "/users/self")
```

---

## Phase 4: All Other Mixins — Mechanical Transform

The core pattern for every mixin method is identical. Here's the transform recipe:

### 4.0 Universal Transform Pattern

**Before** (requests):
```python
async def some_method(self, ...):
    await self.ensure_authenticated()
    response = self.session.get(f"{self.base_url}/some/path", params=params)
    response.raise_for_status()
    return SomeModel.model_validate(parse_json_or_error(response, "/some/path"))
```

**After** (aiohttp):
```python
async def some_method(self, ...):
    await self.ensure_authenticated()
    async with self.session.get(f"{self.base_url}/some/path", params=params) as response:
        response.raise_for_status()
        return SomeModel.model_validate(await parse_json_or_error(response, "/some/path"))
```

**Transform rules**:
1. `self.session.get(...)` → `async with self.session.get(...) as response:`
2. `self.session.post(url, json=data)` → `async with self.session.post(url, json=data) as response:`
3. `self.session.patch(url, json=data)` → `async with self.session.patch(url, json=data) as response:`
4. `self.session.options(url)` → `async with self.session.options(url) as response:`
5. `response.status_code` → `response.status`
6. `response.text` → `await response.text()`
7. `response.json()` → `await response.json()`
8. `parse_json_or_error(response, ep)` → `await parse_json_or_error(response, ep)`
9. `response.url` → `str(response.url)`
10. `time.sleep(x)` → `await asyncio.sleep(x)`
11. Add `await self._ensure_session()` at the start of `ensure_authenticated()` (which all methods call)

### 4.1 `client/simulation.py` (38 `self.session` calls — most complex)

**`_raise_http_error_with_payload`** — currently `@staticmethod`, must become `async`:
```python
@staticmethod
async def _raise_http_error_with_payload(response, endpoint: str) -> None:
    if response.status < 400:  # was: status_code
        return
    try:
        payload = await parse_json_or_error(response, endpoint)
        detail = json.dumps(payload, ensure_ascii=False)
    except Exception:
        detail = (await response.text() or "")[:500]  # was: response.text
    raise RuntimeError(
        f"Request failed at {endpoint} | status={response.status} | detail={detail}"
    )
```

All callers of `_raise_http_error_with_payload` must add `await`.

**`create_simulation()`** — has two sequential requests (POST then GET). Must nest or extract data from each `async with` block:
```python
async def create_simulation(self, simulation_data):
    await self.ensure_authenticated()
    payload = self._build_simulation_payload(simulation_data)

    async with self.session.post(f"{self.base_url}/simulations", json=payload) as response:
        await self._raise_http_error_with_payload(response, "/simulations")
        location = response.headers.get("Location", "")
        if not location:
            raise RuntimeError("...")
        simulation_id = location.rstrip("/").split("/")[-1]

    # Second request — separate async with block
    async with self.session.get(location) as sim_progress:
        await self._raise_http_error_with_payload(sim_progress, "/simulations/{id}")
        snapshot_raw = await parse_json_or_error(sim_progress, "/simulations/{id}")
        snapshot = SimulationSnapshot.model_validate(snapshot_raw)
        self._raise_simulation_error_if_any(snapshot)
        retry_after = sim_progress.headers.get("Retry-After")
        done = retry_after in (None, "0", "0.0")

    return SimulationCreateResponse(...)
```

**`wait_for_simulation()`** — polling loop with `self.session.get()` inside:
```python
for poll_index in range(1, max_polls + 1):
    async with self.session.get(location) as response:
        await self._raise_http_error_with_payload(response, "/simulations/{id}")
        snapshot_raw = await parse_json_or_error(response, "/simulations/{id}")
        ...
        retry_after = response.headers.get("Retry-After")
        done = retry_after in (None, "0", "0.0")
        if done:
            return SimulationWaitResponse(...)
    await async_sleep(float(retry_after or 1))
```

**`create_multi_simulation()`** and **`wait_for_multi_simulation()`** — same pattern. Each `self.session.get(child_url)` becomes `async with self.session.get(child_url) as child_resp:`.

**`run_selection()`** — simple GET, straightforward transform.

### 4.2 `client/alpha.py` (8 `self.session` calls)

**`get_alpha_details()`** — simple GET.

**`check_alpha()`** — polling loop, same pattern as `wait_for_simulation`.

**`submit_alpha()`** — POST then polling GET. Two sequential `async with` blocks. Note: `response.status_code` → `response.status` in all the status checks (201, 403, 404).

**`set_alpha_properties()`** — PATCH request.

**`performance_comparison()`** — GET with status_code check for 404.

**`get_user_alphas()`** — simple GET.

**`_parse_check_response()`** and **`_parse_submit_checks()`** — these are called with a response object. They call `parse_json_or_error(response, ...)`. Since the response body must be read inside `async with`, we have two options:
- **Option A**: Make these methods async and call them inside the `async with` block.
- **Option B**: Pre-parse the JSON before calling these methods, pass the dict.

**Chosen: Option A** — make them async, call inside `async with`. This is cleaner because they also read `response.status_code` → `response.status`.

```python
async def _parse_check_response(self, alpha_id, response, polls):
    body = await parse_json_or_error(response, f"/alphas/{alpha_id}/check")
    ...
    return AlphaCheckResponse(
        ...
        status_code=response.status,  # was: response.status_code
        ...
    )
```

### 4.3 `client/alpha_recordsets.py` (1 `self.session` call + `time.sleep`)

```python
async def get_record_set_data(self, alpha_id, record_set_name):
    await self.ensure_authenticated()
    ...
    for _ in range(max_retries):
        async with self.session.get(f"{self.base_url}{endpoint}") as response:
            response.raise_for_status()
            retry_after = float(response.headers.get("Retry-After", 0))
            if retry_after > 0:
                await asyncio.sleep(retry_after)  # was: time.sleep
                continue
            text = await response.text()
            if not text.strip():
                await asyncio.sleep(2)  # was: time.sleep
                continue
            return AlphaRecordSetResponse.model_validate(
                await parse_json_or_error(response, endpoint)
            )
```

**Note**: `import time` → `import asyncio` (add if not present). Remove `time` import if no longer used.

**IMPORTANT**: The `response.text` check and `parse_json_or_error` must both happen inside the `async with` block. But we also `continue` the loop from inside the block. This works fine — `continue` exits the `async with` block (which closes the response), then continues the `for` loop.

However, there's a subtlety: if we `continue` after reading `response.text()`, we need to re-read `parse_json_or_error` on the *same* response. Since we already called `await response.text()`, calling `await response.json()` inside `parse_json_or_error` will fail (body already consumed). 

**Fix**: Read the body once, then parse:
```python
async with self.session.get(...) as response:
    response.raise_for_status()
    retry_after = float(response.headers.get("Retry-After", 0))
    if retry_after > 0:
        pass  # will continue after exiting async with
    else:
        body_text = await response.text()
        if not body_text.strip():
            pass  # will continue
        else:
            import json
            parsed = json.loads(body_text)
            return AlphaRecordSetResponse.model_validate(parsed)
# Outside async with:
if retry_after > 0:
    await asyncio.sleep(retry_after)
    continue
await asyncio.sleep(2)
continue
```

Actually, simpler approach — use `await response.read()` to buffer the body, then parse:
```python
async with self.session.get(...) as response:
    response.raise_for_status()
    retry_after = float(response.headers.get("Retry-After", 0))
    if retry_after > 0:
        await asyncio.sleep(retry_after)
        continue
    body = await response.json(content_type=None)  # content_type=None skips MIME check
    if body is None:
        await asyncio.sleep(2)
        continue
    return AlphaRecordSetResponse.model_validate(body)
```

Wait — the original checks `response.text.strip()` for empty body. With aiohttp, we can check `await response.text()` first:
```python
async with self.session.get(...) as response:
    response.raise_for_status()
    retry_after = float(response.headers.get("Retry-After", 0))
    if retry_after > 0:
        await asyncio.sleep(retry_after)
        continue
    text = await response.text()
    if not text.strip():
        await asyncio.sleep(2)
        continue
    import json
    return AlphaRecordSetResponse.model_validate(json.loads(text))
```

This is the cleanest approach. Use `json.loads(text)` instead of `await response.json()` since we already consumed the body as text.

### 4.4 `client/correlation.py` (1 `self.session` call)

**`_fetch_correlation()`** — simple GET inside retry loop. Already uses `asyncio.sleep`. Just wrap in `async with`.

### 4.5 `client/data.py` (2 `self.session` calls)

**`get_datasets()`** — simple GET.
**`get_datafields()`** — GET inside pagination loop. Each iteration wraps in `async with`.

### 4.6 `client/community.py` (8 `self.session` calls)

All simple GETs. Mechanical transform.

**`_resolve_user_id()`** — already `async def`, just needs `async with` wrapping for the session call.
```python
async def _resolve_user_id(self, user_id):
    if user_id:
        return user_id
    async with self.session.get(f"{self.base_url}/users/self") as response:
        response.raise_for_status()
        user = UserSelfLite.model_validate(await parse_json_or_error(response, "/users/self"))
        return user.id
```

### 4.7 `client/operators.py` (1 `self.session` call)

Simple GET. Mechanical transform.

### 4.8 `client/simulation_settings.py` (1 `self.session` call)

**`get_platform_setting_options()`** — uses `self.session.options()` (HTTP OPTIONS method). aiohttp supports this via `session.options(url)`.

---

## Phase 5: `client/user.py` — `_get_json` Helper

**File**: `src/wqb_mcp/client/user.py`

**`_get_json()`** is a sync helper used by multiple methods. Must become async:

```python
async def _get_json(self, path: str, params=None) -> Dict[str, Any]:
    async with self.session.get(f"{self.base_url}{path}", params=params) as response:
        response.raise_for_status()
        return await parse_json_or_error(response, path)
```

All callers already `await` the outer method, but `_get_json` itself is called without `await` currently. Must add `await`:
- `get_user_profile`: `return UserProfileResponse.model_validate(await self._get_json(...))`
- `get_messages`: `payload = await self._get_json(...)`
- `get_user_activities`: `return UserActivitiesResponse.model_validate(await self._get_json(...))`
- `get_pyramid_multipliers`: `return PyramidMultipliersResponse.model_validate(await self._get_json(...))`

**`get_pyramid_alphas()`** — uses `self.session.get()` directly (not `_get_json`). Wrap in `async with`.

**`get_daily_and_quarterly_payment()`** — two sequential GETs. Two `async with` blocks:
```python
async with self.session.get(f"{self.base_url}{base_path}") as base_response:
    base_response.raise_for_status()
    base_payments = await parse_json_or_error(base_response, base_path)

async with self.session.get(f"{self.base_url}{other_path}") as other_response:
    other_response.raise_for_status()
    other_payments = await parse_json_or_error(other_response, other_path)
```

---

## Phase 6: `forum.py` — Cookie Transfer Adaptation

**File**: `src/wqb_mcp/forum.py`

**Current code** (line 219):
```python
cookies = brain_client.session.cookies
playwright_cookies = []
for cookie in cookies:
    cookie_dict = {
        'name': cookie.name,
        'value': cookie.value,
        'domain': cookie.domain,
        'path': cookie.path,
        'secure': cookie.secure,
        'httpOnly': 'HttpOnly' in cookie._rest,
        'sameSite': 'Lax'
    }
    if cookie.expires:
        cookie_dict['expires'] = cookie.expires
    playwright_cookies.append(cookie_dict)
```

**After** (aiohttp cookie jar):
```python
playwright_cookies = []
for cookie in brain_client.session.cookie_jar:
    cookie_dict = {
        'name': cookie.key,           # was: cookie.name
        'value': cookie.value,         # same
        'domain': cookie['domain'],    # was: cookie.domain
        'path': cookie['path'],        # was: cookie.path
        'secure': cookie['secure'],    # was: cookie.secure (bool → str)
        'httpOnly': bool(cookie['httponly']),  # was: 'HttpOnly' in cookie._rest
        'sameSite': 'Lax'
    }
    expires = cookie['expires']
    if expires:
        cookie_dict['expires'] = expires  # may need conversion
    playwright_cookies.append(cookie_dict)
```

**Note**: aiohttp's cookie jar iterates `http.cookies.Morsel` objects. The attribute access is different from `requests.cookies.Cookie`:
- `cookie.name` → `cookie.key`
- `cookie.domain` → `cookie['domain']`
- `cookie.path` → `cookie['path']`
- `cookie.secure` → `cookie['secure']` (string, not bool)
- `cookie.expires` → `cookie['expires']` (string, not int)
- `cookie._rest` → `cookie['httponly']`

The `expires` field in Morsel is a string (e.g., "Thu, 01 Jan 2026 00:00:00 GMT"). Playwright expects a Unix timestamp (float). Need to convert:
```python
from email.utils import parsedate_to_datetime
if expires:
    try:
        dt = parsedate_to_datetime(expires)
        cookie_dict['expires'] = dt.timestamp()
    except Exception:
        pass
```

---

## Phase 7: Session Lifecycle Management

### 7.1 Where to call `_ensure_session()`

Add `await self._ensure_session()` at the top of `ensure_authenticated()`. Since every mixin method calls `await self.ensure_authenticated()` first, this guarantees the session exists before any HTTP call.

```python
async def ensure_authenticated(self):
    await self._ensure_session()  # ADD THIS
    if not await self.is_authenticated():
        ...
```

Also add to `authenticate()` directly (since it's called before `ensure_authenticated` on first login):
```python
async def authenticate(self, email, password):
    await self._ensure_session()
    ...
```

### 7.2 Session cleanup

The MCP server runs as a long-lived process. The session should be closed on shutdown. Options:

**Option A**: Register an `atexit` handler (won't work — atexit is sync).
**Option B**: Add cleanup to the MCP server lifecycle. FastMCP may have shutdown hooks.
**Option C**: Don't explicitly close — aiohttp will warn but it's acceptable for a long-lived server process.

**Chosen: Option B** — Add a shutdown hook if FastMCP supports it. Otherwise, rely on process exit. The `close()` method exists for testing.

### 7.3 `is_authenticated()` must also call `_ensure_session()`

Since `is_authenticated()` accesses `self.session.cookie_jar`, it needs the session to exist:
```python
async def is_authenticated(self) -> bool:
    await self._ensure_session()
    ...
```

---

## Phase 8: Files NOT Changed

| File | Reason |
|---|---|
| `config.py` | No HTTP calls |
| `server.py` | No HTTP calls |
| `setup.py` | No HTTP calls |
| `tools/*.py` | No changes needed — they call `await brain_client.method()` which is already the correct pattern |

---

## Complete File-by-File Change Summary

### `pyproject.toml`
- Add `"aiohttp"` to dependencies

### `src/wqb_mcp/utils.py`
- `parse_json_or_error`: `def` → `async def`, `response.json()` → `await response.json()`, `response.text` → `await response.text()`, `response.status_code` → `response.status`
- Add `import aiohttp` (for type hint, optional)

### `src/wqb_mcp/client/__init__.py`
- `import requests` → `import aiohttp`
- `self.session = requests.Session()` → `self.session = None`
- Add `_ensure_session()` async method
- Add `close()` async method
- Remove `self.session.timeout = 30` and `self.session.headers.update({...})`
- Add `self._default_headers` and `self._timeout`

### `src/wqb_mcp/client/auth.py`
- All `self.session.post/get(...)` → `async with self.session.post/get(...) as response:`
- `response.status_code` → `response.status`
- `self.session.cookies.clear()` → `self.session.cookie_jar.clear()`
- `self.session.cookies.get('t')` → `self._get_cookie('t')`
- `self.session.auth = None` → remove (no equivalent needed)
- `response.url` → `str(response.url)`
- Add `_get_cookie()` helper method
- `parse_json_or_error(response, ...)` → `await parse_json_or_error(response, ...)`
- Add `await self._ensure_session()` to `authenticate()` and `is_authenticated()`

### `src/wqb_mcp/client/simulation.py`
- All `self.session.post/get(...)` → `async with self.session.post/get(...) as response:`
- `_raise_http_error_with_payload`: `@staticmethod` → `@staticmethod async`, `response.status_code` → `response.status`, `response.text` → `await response.text()`
- All callers: `self._raise_http_error_with_payload(...)` → `await self._raise_http_error_with_payload(...)`
- `parse_json_or_error(...)` → `await parse_json_or_error(...)`

### `src/wqb_mcp/client/alpha.py`
- All `self.session.get/post/patch(...)` → `async with ...`
- `response.status_code` → `response.status`
- `_parse_check_response` and `_parse_submit_checks`: add `async`, add `await` on `parse_json_or_error`, `response.status_code` → `response.status`
- `parse_json_or_error(...)` → `await parse_json_or_error(...)`

### `src/wqb_mcp/client/alpha_recordsets.py`
- `self.session.get(...)` → `async with self.session.get(...) as response:`
- `time.sleep(...)` → `await asyncio.sleep(...)`
- `import time` → `import asyncio`
- `response.text.strip()` → `(await response.text()).strip()`
- `parse_json_or_error(...)` → use `json.loads(text)` since body already consumed as text

### `src/wqb_mcp/client/correlation.py`
- `self.session.get(...)` → `async with ...`
- `parse_json_or_error(...)` → `await parse_json_or_error(...)`

### `src/wqb_mcp/client/data.py`
- `self.session.get(...)` → `async with ...`
- `parse_json_or_error(...)` → `await parse_json_or_error(...)`

### `src/wqb_mcp/client/community.py`
- All `self.session.get(...)` → `async with ...`
- `_resolve_user_id`: already `async def`, just wrap session call in `async with`
- `parse_json_or_error(...)` → `await parse_json_or_error(...)`

### `src/wqb_mcp/client/user.py`
- `_get_json`: `def` → `async def`, wrap in `async with`
- All callers of `_get_json`: add `await`
- `self.session.get(...)` → `async with ...`
- `parse_json_or_error(...)` → `await parse_json_or_error(...)`

### `src/wqb_mcp/client/operators.py`
- `self.session.get(...)` → `async with ...`
- `parse_json_or_error(...)` → `await parse_json_or_error(...)`

### `src/wqb_mcp/client/simulation_settings.py`
- `self.session.options(...)` → `async with self.session.options(...) as response:`
- `parse_json_or_error(...)` → `await parse_json_or_error(...)`

### `src/wqb_mcp/forum.py`
- Cookie iteration: `brain_client.session.cookies` → `brain_client.session.cookie_jar`
- Morsel attribute access changes (see Phase 6)
- Note: `ForumScraper.self.session` (its own `requests.Session`) is unused for HTTP — no change needed there

---

## Verification Steps

### Step 1: Static analysis
```bash
cd /Users/lizehan/code/quant/wqb-mcp
# Check for any remaining sync session calls
grep -rn "self\.session\.\(get\|post\|patch\|put\|delete\|options\)" src/wqb_mcp/client/ --include="*.py"
# Should return 0 lines (all converted to async with)

# Check for remaining time.sleep in async context
grep -rn "time\.sleep" src/wqb_mcp/client/ --include="*.py"
# Should return 0 lines

# Check for remaining response.status_code
grep -rn "\.status_code" src/wqb_mcp/client/ --include="*.py"
# Should return 0 lines (all converted to .status)
# Note: Pydantic model fields named status_code are fine

# Check for sync parse_json_or_error calls (should all be awaited)
grep -rn "parse_json_or_error" src/wqb_mcp/ --include="*.py" | grep -v "await\|async def\|^#"
# Should return 0 lines
```

### Step 2: Import check
```bash
cd /Users/lizehan/code/quant/wqb-mcp
python -c "from wqb_mcp.client import brain_client; print('Import OK')"
```

### Step 3: Functional test — authenticate
```bash
python -c "
import asyncio
from wqb_mcp.client import brain_client
async def test():
    await brain_client.authenticate('test@example.com', 'password')
asyncio.run(test())
"
```

### Step 4: MCP server smoke test
```bash
wqb-mcp  # Start server, verify it boots without errors
```

---

## Risk Areas & Mitigations

| Risk | Mitigation |
|---|---|
| Response body consumed twice | Always read body once inside `async with`, store in variable |
| `async with` scope — accessing response after block exits | Extract all needed data (status, headers, body) inside the block |
| Cookie jar differences | Test auth flow end-to-end; verify JWT cookie persists across requests |
| `aiohttp.ClientSession` created outside event loop | Lazy creation via `_ensure_session()` |
| `response.text` is now async method, not property | Search-and-replace all `response.text` → `await response.text()` |
| `response.url` is `yarl.URL`, not `str` | Wrap with `str()` where string is expected (auth.py line 105) |
| Forum cookie transfer breaks | Test forum tools after migration; Morsel API differs from requests Cookie |
| `_raise_http_error_with_payload` becomes async | All callers must `await` — grep to verify |

---

## Estimated Effort

| Phase | Files | Estimated Changes |
|---|---|---|
| Phase 0 | 1 | 1 line |
| Phase 1 | 1 | ~10 lines |
| Phase 2 | 1 | ~25 lines |
| Phase 3 | 1 | ~80 lines |
| Phase 4 | 7 files | ~200 lines total |
| Phase 5 | 1 | ~30 lines |
| Phase 6 | 1 | ~15 lines |
| Phase 7 | verification | — |
| **Total** | **13 files** | **~360 lines changed** |
