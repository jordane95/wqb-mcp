# Tool Refactoring Workflow

Steps to refactor an MCP tool from raw dict returns to typed Pydantic models with compact text output.

## 1. Document the API response

- Hit the raw API endpoints and record the actual JSON response structure
- Save to `docs/<feature>_api.md`
- Note shared structures vs differences between endpoints

## 2. Define Pydantic models in the client file

- Put models in the same file as the client mixin (e.g. `client/correlation.py`), not a central `models.py`
- Use `Field(alias="...")` for reserved names (e.g. `schema`)
- Use `str(Enum)` for constrained string values (e.g. endpoint types)
- Enum values should match API values directly to reduce variable mapping

## 3. Add `__str__` to response models

- LLMs consume tool output as text — compact markdown/text saves tokens vs JSON
- Keep it concise: one line per sub-result, pipe-separated fields
- Example: `- prod: max=0.7236, FAIL | 2 correlated | top: abc(0.93)`

## 4. Simplify the client method

- Use the enum value directly for endpoint paths and log labels
- Validate inputs via enum (invalid values raise `ValueError` automatically)
- Raise on all failures after retries (no silent empty returns)
- Handle null/missing data explicitly (e.g. `max=null` → auto-pass, not an error)
- Only extract fields that are meaningful for the response type

## 5. Update the tool layer

- Return `str(result)` for token-efficient text output
- **Do NOT annotate the return type** on the tool function — omit `-> str`, `-> dict`, etc.
  - `-> str` or any primitive: FastMCP wraps in `{"result": ...}` structured output, wasting tokens
  - `-> BaseModel`: FastMCP sends full JSON via `pydantic_core.to_json()`
  - No annotation: FastMCP sends only the plain `TextContent` — cleanest output
- Keep shorthand logic (e.g. `"both"` → `[PROD, SELF]`) in the tool layer, not the client
- Remove try/except — let FastMCP convert exceptions to `ToolError` automatically
- Update the docstring with valid parameter values (this is the tool description LLMs see)

## 6. Test

- Valid inputs: each enum value individually, combined shortcuts
- Invalid inputs: verify clean error message from enum validation
- Edge cases: null/empty API responses
- Reconnect MCP (`/mcp`) and test via tool calls
