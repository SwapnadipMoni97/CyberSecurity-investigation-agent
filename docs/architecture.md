# Architecture and project structure

## System architecture

The diagram below uses plain ASCII so it stays readable in GitHub, editors, and terminals.
Read it from top to bottom: events enter the store, while an analyst's request starts the
investigation path.

```text
  CURRENT EVENT INPUT
  +---------------------------+       +---------------------------+
  | Synthetic sample JSON     |------>| FastAPI validates event   |
  | Or normalized event POST  |       | against shared schema     |
  +---------------------------+       +-------------+-------------+
                                                    |
                                                    v
                                      +---------------------------+
                                      | SQLite event store        |
                                      | normalized + raw record   |
                                      +-------------+-------------+
                                                    ^
                                                    | read matching events
                                                    |
  CURRENT INVESTIGATION                          |
  +---------------------------+       +-----------+---------------+
  | Analyst in browser        |------>| FastAPI investigation    |
  | question + optional alert |       | endpoint                 |
  +---------------------------+       +-------------+------------+
                                                    |
                                                    v
                                      +---------------------------+
                                      | LangGraph workflow        |
                                      | gather -> analyze/report  |
                                      +-------------+-------------+
                                                    |
                                                    v
                                      +---------------------------+
                                      | Read-only evidence search |
                                      | alert / keyword / actor   |
                                      | IP correlation            |
                                      +---------------------------+
                                                    |
                                                    v
                                      +---------------------------+       +----------------------+
                                      | Timeline and findings     |------>| Optional hosted model|
                                      | computed in application   |       | summary synthesis    |
                                      +-------------+-------------+       +----------+-----------+
                                                    |                                |
                                                    +----------------+---------------+
                                                                     |
                                                                     v
                                      +---------------------------+       +---------------------------+
                                      | Save report in SQLite     |------>| Return report to browser  |
                                      | investigation case        |       | findings + evidence IDs   |
                                      +---------------------------+       +---------------------------+

  FUTURE (NOT IMPLEMENTED)
  +--------------------------------------+       +---------------------------+
  | Live app connectors                  |------>| Durable queue + workers   |
  | AWS / Okta / GitHub / cloud / SaaS   |       | retries + status tracking|
  +--------------------------------------+       +-------------+-------------+
                                                               |
                                                               +--> event store
```

The current runtime uses a single FastAPI process and a local SQLite file. There is no message
queue or background worker yet. The future connectors and queue shown at the bottom are design
targets, not integrations that are already available.

## Investigation workflow graph

```text
  +-------+       +-------------------------+       +--------------------------+
  | START |------>| 1. GATHER EVIDENCE      |------>| 2. ANALYZE AND REPORT    |
  +-------+       |                         |       |                          |
                  | Call read-only search   |       | Sort events by timestamp|
                  +------------+------------+       | Apply deterministic rules|
                               |                    | Draft summary and gaps   |
                               v                    +------+--------------+----+
                  +-------------------------+              |              |
                  | SQLite event records    |              |              |
                  | Query by alert / terms  |              v              v
                  | Expand by actor or IP    |       +-------------+  +----------------+
                  +-------------------------+       | Rule-based  |  | Optional model |
                                                    | findings    |  | summary only  |
                                                    +------+------+  +-------+--------+
                                                           |                 |
                                                           +--------+--------+
                                                                    |
                                                                    v
                                                   +-----------------------------+
                                                   | Report with evidence IDs    |
                                                   | Save case and return to UI  |
                                                   +--------------+--------------+
                                                                  |
                                                                  v
                                                               +-----+
                                                               | END |
                                                               +-----+
```

The two LangGraph nodes are defined in `src/agent/workflow.py`:

1. **Gather evidence** calls the read-only search tool. With an alert ID, it finds matching
   anchor events, then expands to nearby events that share an actor or IP. Without an alert ID,
   it uses keyword matches within the requested window, falling back to all events in that window
   if the query has no matches.
2. **Analyze and report** orders events by timestamp, computes the summary and findings, and may
   ask the hosted model to rewrite the summary. Finding evidence IDs and the timeline come from
   application code and are not generated by the model.

The current correlation method is deliberately simple. Shared actor or IP values are leads for
analysts; they do not prove that the same person or device generated the events.

## Repository structure

```text
secops-investigation-agent/
├── README.md                      # Project overview and architecture diagram
├── docs/
│   ├── architecture.md            # System, workflow, data flow, module map
│   └── startup-guide.md           # Local, API, model, and Docker instructions
├── Dockerfile                     # Container image for the API and UI
├── pyproject.toml                 # Python package and dependencies
├── .env.example                   # Safe configuration template (no secrets)
├── scripts/
│   └── check_openai_key.py         # One-request API key/model access check
└── src/
    ├── api.py                     # FastAPI routes and app lifecycle
    ├── agent/
    │   └── workflow.py             # LangGraph nodes, findings, optional model call
    ├── data/
    │   ├── repository.py           # SQLite persistence and initial sample loading
    │   └── sample_events.json      # Synthetic cross-source incident
    ├── domain/
    │   └── models.py               # Pydantic event and request models
    ├── tools/
    │   └── evidence_search.py      # Read-only evidence retrieval/correlation
    ├── ui/
    │   └── index.html              # Analyst screen
    ├── ingestion/                  # Reserved for source adapters
    └── observability/              # Reserved for tracing and metrics
```

`ingestion/` and `observability/` are currently empty extension points. Live vendor adapters,
queue/worker processing, production database migrations, authentication, and tenant isolation
remain future work.

## Event and report data flow

1. The app initializes the SQLite schema. If the event table is empty, it inserts the bundled
   synthetic records.
2. `POST /api/events` validates a normalized event and stores its shared fields and original
   `raw` object. Event IDs are unique; re-ingesting an ID replaces that row.
3. The analyst submits a question, optional alert ID, and time window through the UI or API.
4. LangGraph retrieves a bounded set of evidence and correlates alert-related activity.
5. Application code creates a chronological timeline and findings. Each finding carries one or
   more event IDs so an analyst can locate the source records.
6. The report is saved in SQLite and returned to the analyst.

## Model boundary

Hosted model calls are disabled by default. When explicitly enabled and an API key is configured,
the app calls GPT-6.1 Terra through the OpenAI Responses API for a concise plain-language summary.
The prompts identify event data as untrusted; the model is instructed not to follow instructions
inside records or invent facts. The model does not retrieve data directly, modify evidence, or
perform response actions. The current build sends the selected records and computed report to the
provider, so use synthetic or appropriately sanitized evidence for portfolio demonstrations.

## Deployment boundary

The Dockerfile packages the current app, but the application is still a single-user local demo.
Do not put it on a public URL with real evidence until authentication, tenant isolation, secret
management, TLS, durable queueing, retention controls, and production storage have been designed
and implemented. The Docker container currently uses SQLite; a hosted environment needs persistent
storage or a managed database before cases can survive container replacement.
