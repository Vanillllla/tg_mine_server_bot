# Minecraft Web Panel

First backend scaffold for a Minecraft multi-server web panel.

The project follows `minecraft_web_panel_tz.md`: FastAPI is the single control
center for Web UI and Telegram bot, and it manages one active Minecraft Server
Instance at a time.

## What is included

- FastAPI application entrypoint.
- JSON-backed `panel.json` and `servers.json` storage.
- `ServerInstanceService` for creating, listing, updating and activating server
  instances.
- `MinecraftServerManager` for starting, stopping, killing and sending stdin
  commands to the active server process.
- In-memory `LogBuffer` with recent logs and WebSocket subscribers.
- API routes for stage 1:
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `GET /api/auth/me`
  - `POST /api/auth/invite-login`
  - `GET|POST|DELETE /api/auth/invite`
  - `GET /api/servers`
  - `POST /api/servers`
  - `GET /api/servers/active`
  - `POST /api/servers/{server_id}/activate`
  - `POST /api/servers/active/start`
  - `POST /api/servers/active/stop`
  - `POST /api/servers/active/restart`
  - `POST /api/servers/active/kill`
  - `GET /api/servers/active/status`
  - `GET /api/servers/active/work-data`
  - `GET /api/servers/active/logs/recent`
  - `POST /api/servers/active/console/command`
  - `WS /ws/servers/active/console`

## Local run

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
MC_PANEL_HOME=./runtime/mc-panel .venv/bin/uvicorn app.main:app --reload
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
$env:MC_PANEL_HOME = ".\runtime\mc-panel"
.\.venv\Scripts\uvicorn app.main:app --reload
```

Default admin credentials for the MVP are `admin` / `change-me`. Override them in
deployment with:

```bash
export MC_PANEL_ADMIN_USERNAME=admin
export MC_PANEL_ADMIN_PASSWORD='change-me'
```

On Windows PowerShell set environment variables before starting uvicorn:

```powershell
$env:MC_PANEL_ADMIN_USERNAME = "admin"
$env:MC_PANEL_ADMIN_PASSWORD = "change-me"
python -m uvicorn app.main:app --reload
```

An admin can create or close the public user invite link in `Settings`. Users
who enter through that link only receive safe permissions: start the active
server and view status/metrics.

For Linux VM deployment set:

```bash
export MC_PANEL_HOME=/srv/mc-panel
```

## Runtime layout

On startup the backend creates:

```text
MC_PANEL_HOME/
  config/
    panel.json
    servers.json
  data/
  uploads/
  backups/
  servers/
```
