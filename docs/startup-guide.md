# Startup guide

This guide starts the local synthetic-data demo. It does not require a live AWS, Okta, or GitHub
account and does not require an OpenAI API key.

## 1. Requirements

- Python 3.11 or newer
- PowerShell on Windows (commands below)
- Internet access for installing Python packages
- Optional: Docker Desktop for the container path

## 2. Create and start the local app

From the workspace root:

```powershell
cd secops-investigation-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uvicorn src.api:app --reload
```

If PowerShell blocks activation, use this for the current terminal only, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Open <http://127.0.0.1:8000>. FastAPI's interactive API page is at
<http://127.0.0.1:8000/docs>. Stop the server with **Ctrl+C**.

The first startup creates `data/secops.db` and inserts the synthetic event set if the database
does not already contain events. The included timeline links a suspicious Okta session, GitHub
token and repository activity, and AWS role/policy/secret events.

## 3. Run the sample investigation

The browser UI is prefilled for alert `ALT-1001`; click **Investigate sample incident**.
Alternatively, from a second PowerShell window:

```powershell
$body = @{
  question = 'Investigate the suspicious privilege escalation and related activity'
  alert_id = 'ALT-1001'
  time_window_hours = 72
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/investigations `
  -ContentType 'application/json' `
  -Body $body
```

The response contains a summary, key findings with evidence IDs, ordered timeline, scope, gaps,
suggested follow-up, and the model mode used. The API's Swagger page also lets you submit requests.

## 4. Ingest a normalized event

`POST /api/events` accepts the common event shape. This is a local ingestion endpoint; it is not
a live AWS/Okta/GitHub connector. Example:

```powershell
$event = @{
  event_id = 'DEMO-9001'
  source = 'aws'
  timestamp = '2026-10-30T10:12:00Z'
  event_type = 'ConsoleLogin'
  actor = 'alex.chen@example.test'
  action = 'login'
  outcome = 'success'
  ip_address = '198.51.100.24'
  resource = 'AWS account 111122223333'
  details = @{ mfa = 'passed' }
  raw = @{ eventName = 'ConsoleLogin'; note = 'synthetic example' }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/events `
  -ContentType 'application/json' `
  -Body $event
```

The event can then be found through `GET /api/events` or investigated from the UI/API. Use unique
event IDs. The current local store replaces an existing row if the same ID is ingested again.

## 5. Optional hosted GPT-6.1 Terra synthesis

The deterministic workflow is the default and incurs no model API charges. To enable hosted
summary synthesis:

1. Create an API key in the [OpenAI API Platform](https://platform.openai.com/api-keys) and make
   sure API billing is configured. API usage billing is separate from a ChatGPT subscription.
2. Put the key in the local `secops-investigation-agent/.env` file. Do not commit or share it.
3. Set these values in `.env`:

   ```dotenv
   OPENAI_API_KEY=your-secret-key
   OPENAI_MODEL=gpt-6.1-terra
   USE_HOSTED_MODEL=true
   ```

4. Verify the key and model access with one short API request:

   ```powershell
   python scripts/check_openai_key.py
   ```

   A success message confirms the API accepted the key and the selected model. This makes one
   billable request with a short prompt. `/api/health` reports `hosted` when the setting and a
   non-empty key are present; it does not validate the key by itself.

5. Restart Uvicorn so the app uses the `.env` settings.

The hosted call is made only for the report summary after deterministic retrieval and analysis.
The model sees selected event records and the computed report. Use synthetic or sanitized records
and configure usage/spend limits in the API Platform before experimenting.

To switch back to local-only mode, set `USE_HOSTED_MODEL=false` and restart the app. The key may
remain in `.env`, but it is not used in that mode.

## 6. Run with Docker (optional)

From `secops-investigation-agent/`:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker build -t secops-investigation-agent .
docker run --rm -p 8000:8000 `
  -v secops-agent-data:/app/data `
  --env-file .env `
  secops-investigation-agent
```

Then open <http://localhost:8000>. The named volume preserves the SQLite database across
container replacement. If you do not want hosted synthesis, keep `USE_HOSTED_MODEL=false`; do not
add a key to the container environment.

## 7. Configuration reference

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | unset | Optional server-side provider secret |
| `OPENAI_MODEL` | `gpt-6.1-terra` | Hosted summary model ID |
| `USE_HOSTED_MODEL` | `false` | Explicitly enables hosted summary synthesis |
| `SECOPS_DATABASE_PATH` | `./data/secops.db` | SQLite database path, relative to project directory unless absolute |

## 8. Troubleshooting

- **`uvicorn` not found:** activate `.venv` and rerun `python -m pip install -e .`.
- **Port 8000 already in use:** start with `uvicorn src.api:app --reload --port 8001` and open
  `http://127.0.0.1:8001`.
- **PowerShell activation is blocked:** use the process-scoped execution policy command above.
- **Changes to `.env` don't take effect:** stop and restart Uvicorn.
- **No sample events appear:** the sample set is loaded only when the events table is empty. For a
  fresh demo database, stop the app, move/delete `data/secops.db`, and restart. This removes saved
  local demo cases and ingested events too.
- **Hosted synthesis falls back to deterministic mode:** verify the API key, model access, billing,
  and `USE_HOSTED_MODEL=true`; inspect the returned `model_mode`/`model_note` fields.

## Scope reminder

This is a local portfolio MVP without authentication or tenant isolation. Do not expose it publicly
or send production security logs to it. Live vendor connectors, automated queue-backed processing,
durable hosted database, image evidence, and response actions are not implemented in this version.
