# whoop-mcp

[MCP](https://modelcontextprotocol.io/) server (stdio) for the [WHOOP Developer API](https://developer.whoop.com/api) v2. It uses OAuth 2.0 authorization code flow with refresh tokens (`offline` scope), persists tokens on disk, and exposes typed tools for profile, cycles, recovery, sleep, and workouts.

## Prerequisites

- **Python** 3.11+
- **[uv](https://docs.astral.sh/uv/)** for installs and `uv run …`

## Setup

```bash
cd whoop-mcp
uv sync --all-groups
cp .env.example .env
# Edit .env — see below
```

## WHOOP Developer Dashboard

1. Create an OAuth application in the WHOOP developer console.
2. Set **Client ID** and **Client secret** in `.env` as `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET`.
3. Register a **redirect URI** that matches **exactly** (scheme, host, port, path, no stray slashes). For local login the server binds to the host/port in that URI, so the port must be present. Example used throughout the project:

   `http://127.0.0.1:8780/callback`

   Put the same value in `WHOOP_REDIRECT_URI`.

A mismatch with the dashboard breaks OAuth.

## Login (one-time)

With `.env` configured:

```bash
uv run whoop-mcp login
```

After `uv sync`, you can also run the dedicated console script (same behavior as `whoop-mcp login`):

```bash
uv run whoop-mcp-login
```

The CLI starts a localhost HTTP listener on the host/port from `WHOOP_REDIRECT_URI`, opens the browser (unless `--no-browser`), exchanges the code for tokens, and writes them to the token file.

## Token storage

Default path: **`~/.config/whoop-mcp/tokens.json`**. Override with `WHOOP_TOKEN_STORE_PATH`.

## Configuration reference

| Variable | Role |
| --- | --- |
| `WHOOP_CLIENT_ID` / `WHOOP_CLIENT_SECRET` | OAuth app credentials |
| `WHOOP_REDIRECT_URI` | Registered callback (local example: `http://127.0.0.1:8780/callback`) |
| `WHOOP_DEFAULT_SCOPES` | Space-separated scopes; include `offline` for refresh tokens |
| `WHOOP_TOKEN_STORE_PATH` | Token JSON path (default above) |
| `WHOOP_TOKEN_REFRESH_SKEW_SECONDS` | Refresh access tokens this many seconds **before** expiry (default `60`; range `0`–`600`) |
| `WHOOP_HTTP_TIMEOUT_SECONDS` | OAuth/API HTTP timeout (`1`–`120`, default `30`) |
| `WHOOP_LOG_LEVEL` | `DEBUG` … `CRITICAL` |
| `WHOOP_AUTHORIZATION_URL` / `WHOOP_TOKEN_URL` / `WHOOP_API_BASE_URL` | Optional overrides (defaults match WHOOP docs) |

## MCP tools

Tools return JSON-serializable dicts (Pydantic `model_dump`). Data tools require a successful login and load tokens from disk.

| Tool | Purpose |
| --- | --- |
| `server_ping` | Liveness check |
| `connect_instructions` | OAuth setup steps for the client |
| `auth_status` | Whether a token file exists and basic metadata (no network) |
| `get_profile` | `GET /v2/user/profile/basic` |
| `get_body_measurements` | `GET /v2/user/measurement/body` |
| `list_cycles` / `get_cycle` | Cycle collection and by ID |
| `list_recovery` / `get_latest_recovery` / `get_recovery_for_cycle` | Recovery data |
| `list_sleep` / `get_sleep` / `get_sleep_for_cycle` | Sleep records |
| `list_workouts` / `get_workout` | Workouts |
| `whoop_health_summary` | Snapshot: profile plus latest recovery, sleep, and cycle |

## WHOOP endpoints (reference)

- **Authorize:** `https://api.prod.whoop.com/oauth/oauth2/auth`
- **Token:** `https://api.prod.whoop.com/oauth/oauth2/token`
- **API base:** `https://api.prod.whoop.com/developer`

See [OAuth 2.0 | WHOOP for Developers](https://developer.whoop.com/docs/developing/oauth).

## Development

```bash
uv run pytest
uv run ruff check src tests
```

Run the MCP server (stdio):

```bash
uv run whoop-mcp
```

## License

MIT — see [LICENSE](LICENSE).
