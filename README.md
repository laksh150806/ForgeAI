# ForgeAI

**Autonomous Production Debugging & Remediation Engine**

ForgeAI is a production-oriented debugging and remediation engine that correlates runtime failures with recent code changes, localizes likely regressions, builds evidence-backed fix plans, validates proposed patches, and preserves an auditable incident-to-fix trail.

## Live deployment

- Web: https://forgeai-web-irot.onrender.com
- API: https://forgeai-api-ok42.onrender.com
- Seed benchmark: https://forgeai-api-ok42.onrender.com/api/v1/evaluation/seed

## Vision

ForgeAI is not a generic coding chatbot. The target workflow is:

```
Production Failure / Runtime Evidence
   ↓
Deploy + Commit Correlation
   ↓
Repository / Code Intelligence
   ↓
Root-cause Investigation
   ↓
Evidence-backed Engineering Plan
   ↓
Patch Proposal
   ↓
Sandbox Validation
   ↓
Evaluation + Observability
   ↓
Human-approved PR
```

## Current status

**Phase 10 — Production hardening**

The repository currently contains:

- Next.js + TypeScript web application
- FastAPI backend
- initial product UI
- API health/status endpoints
- environment configuration template
- architecture specification
- production-oriented monorepo layout

## Repository structure

```text
ForgeAI/
├── apps/
│   ├── web/                 # Next.js product UI
│   └── api/                 # FastAPI backend
├── docs/
│   └── ARCHITECTURE.md
├── .env.example
└── .gitignore
```

Planned modules will add repository ingestion, Tree-sitter/AST code intelligence,
hybrid retrieval, agent orchestration, isolated validation, evaluation, and GitHub PR workflows.

## Run locally

### API

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API: `http://localhost:8000`

Health check:

```text
GET /health
```

### Web

```bash
cd apps/web
npm install
npm run dev
```

Web: `http://localhost:3000`

## MVP roadmap

- [x] Project foundation
- [x] Web + API skeleton
- [x] GitHub repository ingestion
- [x] Repository file inventory
- [x] AST-aware code parsing
- [x] Lexical retrieval + symbol-aware ranking
- [x] Task-to-file retrieval layer
- [x] Structured investigation agent
- [x] Structured engineering plan
- [x] Patch/diff generation
- [x] Sandboxed validation
- [x] Execution traces and metrics
- [x] Human-approved GitHub PR creation
- [x] Evaluation benchmark suite
- [x] Production deployment hardening
- [x] Persistent execution traces (Supabase/Postgres)
- [x] Production incident → recent commit correlation
- [x] Runtime evidence → code-level hypothesis cross-check

## Engineering principles

- Evidence before generation
- Explicit agent stages over opaque autonomous loops
- Provider-independent model layer
- Validation before repository writes
- Observable tool calls and model decisions
- Safe failure when evidence is insufficient
- Measurable agent quality

## Why ForgeAI

The project is designed to demonstrate practical skills across:

**AI engineering · agents · RAG · code intelligence · backend · frontend · databases · GitHub automation · testing · security · DevOps · observability · evaluation**

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the current architecture and [docs/FREE_STACK.md](docs/FREE_STACK.md) for the zero-cost deployment plan.


## Repository Intelligence API

Analyze a public GitHub repository:

```http
POST /api/v1/repositories/analyze
Content-Type: application/json

{
  "repository_url": "https://github.com/laksh150806/ForgeAI"
}
```

The response includes repository metadata, file inventory, source-language distribution,
important project files, and files excluded as generated/dependency noise. Set
`GITHUB_TOKEN` for higher GitHub API limits and future private-repository support.


## Code Intelligence API

Rank repository code against an engineering task:

```http
POST /api/v1/code/search
Content-Type: application/json

{
  "repository_url": "https://github.com/laksh150806/ForgeAI",
  "task": "Find the code responsible for GitHub repository URL validation.",
  "limit": 8
}
```

ForgeAI extracts source symbols, chunks code, normalizes identifier tokens, and ranks
evidence using task-term relevance with path and symbol boosts. Semantic embeddings and
persistent indexing are planned as the next retrieval upgrade.


## Hybrid retrieval and investigation

When `OPENAI_API_KEY` is configured, ForgeAI reranks strong lexical candidates with
semantic embeddings using `text-embedding-3-small` by default. Without that key,
retrieval automatically falls back to the deterministic lexical/symbol-aware path.

Run a structured investigation:

```http
POST /api/v1/investigations/run
Content-Type: application/json

{
  "repository_url": "https://github.com/laksh150806/ForgeAI",
  "task": "Repository URL validation is rejecting valid GitHub repositories.",
  "limit": 6
}
```

The response contains a ranked evidence set, a bounded confidence score, a concise
implementation-surface hypothesis, rationale, and next actions. The current investigator
is evidence-driven and deterministic; model-based root-cause synthesis can be added
behind the same response contract later.


## Engineering plans and patch proposals

Generate an evidence-backed implementation plan and, when a model key is configured,
a review-only unified diff:

```http
POST /api/v1/plans/generate
Content-Type: application/json

{
  "repository_url": "https://github.com/laksh150806/ForgeAI",
  "task": "Fix repository URL validation for valid GitHub URLs.",
  "generate_patch": true
}
```

Planning always works from investigation evidence. Patch generation is optional and uses
`OPENAI_API_KEY` or `LLM_API_KEY` with `PATCH_MODEL` (default `gpt-6-luna`).
ForgeAI only accepts patches for files that were actually loaded into model context.
Every patch is preview-only and `approval_required` remains true; Phase 5 performs no
repository writes.


## Sandboxed patch validation

Validate generated patch proposals before any GitHub write is permitted:

```http
POST /api/v1/validation/run
Content-Type: application/json

{
  "repository_url": "https://github.com/laksh150806/ForgeAI",
  "patches": [
    {
      "path": "apps/api/app/main.py",
      "rationale": "example",
      "unified_diff": "--- a/...\n+++ b/...\n@@ ..."
    }
  ]
}
```

ForgeAI clones the repository into a temporary workspace, verifies the unified diff with
`git apply --check`, applies it only to that disposable clone, and then runs fixed
validation commands. When Docker is available, validation executes with network disabled,
all Linux capabilities dropped, a PID/CPU/memory limit, `no-new-privileges`, and a
read-only container filesystem. The container may write only to the disposable repository
mount and temporary storage.

The browser cannot submit arbitrary shell commands. If Docker is unavailable, ForgeAI
performs only a non-executing `git diff --check` fallback and keeps the PR gate blocked.


## End-to-end execution traces

Run ForgeAI's core workflow with one request and receive a stage-by-stage trace:

```http
POST /api/v1/runs/execute
Content-Type: application/json

{
  "repository_url": "https://github.com/laksh150806/ForgeAI",
  "task": "Fix repository URL validation for valid GitHub URLs.",
  "generate_patch": true,
  "validate_patch": true
}
```

The trace records retrieval, investigation, planning/patch generation, and sandbox
validation with per-stage duration, status, structured metadata, errors, total runtime,
evidence count, patch count, validation-command count, retrieval mode, and final PR-gate
state. The current trace is request-scoped; persistent trace storage and cost/token
accounting can be layered onto the same run contract later.


## Human-approved GitHub PR creation

ForgeAI can now close the loop after successful validation:

```http
POST /api/v1/pull-requests/create
Content-Type: application/json

{
  "repository_url": "https://github.com/owner/repository",
  "task": "Fix the reported issue",
  "patches": [...],
  "approved": true
}
```

This endpoint does **not** trust a browser-supplied validation flag. It reruns the full
server-side sandbox validation and refuses to write if the PR gate is closed. It also
requires explicit human approval. When both conditions pass, ForgeAI creates a new
`forgeai/validated-...` branch, writes only the validated files, and opens a pull request
whose body includes task context, changed files, sandbox result, validation checks, and
the approval/validation safety statement.

`GITHUB_TOKEN` must have write permission to the target repository.


## Evaluation benchmark suite

ForgeAI includes a gold-labeled benchmark API for reproducible evaluation:

```http
POST /api/v1/evaluation/benchmark
Content-Type: application/json
```

Each benchmark case specifies a repository, engineering task, expected files, optional
expected symbols, and optionally the expected PR-gate outcome. Retrieval evaluation
reports:

- Top-1 file accuracy
- Recall@K
- Mean Reciprocal Rank (MRR)
- Symbol hit accuracy
- Average retrieval latency

With `run_full_pipeline=true`, the same harness also measures:

- Patch-generation rate
- Validation pass rate
- PR-gate accuracy


### Latest measured live seed benchmark

Externally verified against the deployed API on **2026-10-05**:

- **66.67% Top-1 file accuracy**
- **100% Recall@3**
- **0.8333 MRR**
- **100% symbol hit accuracy**
- **99.67 ms mean task-ranking latency**

These figures are from a **3-case gold-labeled seed benchmark**, not a broad SWE benchmark.
See [docs/BENCHMARKS.md](docs/BENCHMARKS.md) for methodology, baseline comparison, and
limitations.

The seed dataset lives at `benchmarks/forgeai.json`. Reported resume/demo numbers should
come from actual benchmark runs; ForgeAI does not hard-code or invent performance claims.


## Production deployment

ForgeAI is designed to deploy as separate web and API services with optional **Supabase Free Postgres**
trace persistence. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

Production hardening includes:

- environment-driven CORS via `CORS_ORIGINS`
- liveness at `GET /health`
- database-aware readiness at `GET /ready`
- best-effort Postgres persistence for workflow traces
- `GET /api/v1/runs/recent` for recent persisted runs
- secrets supplied only through deployment environment variables

When `DATABASE_URL` is absent, ForgeAI remains functional with a bounded in-memory trace history.
For zero-cost durable traces, use the Supabase Free shared session pooler as documented in
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).


## Production incident correlation

ForgeAI's differentiating workflow begins with a production failure rather than a pull request.

```http
POST /api/v1/incidents/correlate
Content-Type: application/json

{
  "repository_url": "https://github.com/laksh150806/ForgeAI",
  "incident": "Production requests started returning 500 after the latest deploy.",
  "evidence": {
    "error_message": "PaymentTimeout in apps/api/app/services/payments.py",
    "stack_trace": null,
    "logs": [],
    "deploy_sha": "optional-commit-sha"
  },
  "lookback_commits": 10,
  "code_limit": 6
}
```

The correlator shallow-clones bounded Git history, inspects recent commit subjects, changed
files, and diffs, scores them against runtime evidence, boosts an explicitly supplied deploy
SHA, then cross-checks changed files against ForgeAI's code retrieval results. The response
contains ranked suspect commits and a code-level investigation hypothesis. This is the first
step toward the full target flow:

```text
runtime failure → suspect deploy → changed symbols → root cause → patch → validation → approval → PR
```


## Telemetry ingestion and incident timeline reconstruction

ForgeAI can persist normalized production telemetry and reconstruct the causal window around an incident.

Ingest deploy/log/error events:

```http
POST /api/v1/telemetry/events
Content-Type: application/json

{
  "events": [
    {
      "source": "render",
      "event_type": "deploy",
      "severity": "info",
      "service": "payments-api",
      "message": "Deployment completed",
      "deploy_sha": "8f3a2c1"
    },
    {
      "source": "application",
      "event_type": "error",
      "severity": "error",
      "service": "payments-api",
      "message": "PaymentTimeout in capture_payment"
    }
  ]
}
```

Reconstruct the timeline:

```http
POST /api/v1/telemetry/timeline
Content-Type: application/json

{
  "repository_url": "https://github.com/owner/repository",
  "service": "payments-api",
  "lookback_minutes": 120,
  "lookback_commits": 20
}
```

ForgeAI finds the first failure, selects the nearest deploy that happened before it,
collects surrounding telemetry as runtime evidence, and then runs the commit/diff +
code-retrieval correlator. Telemetry is persisted in Supabase/Postgres when
`DATABASE_URL` is configured and falls back to bounded in-memory storage otherwise.


## Automatic Render telemetry adapter

ForgeAI can poll Render's REST API for recent deploys and logs, normalize them into
ForgeAI telemetry, persist them, and optionally reconstruct an incident timeline in the
same request.

Server-side configuration:

```env
RENDER_API_KEY=...
RENDER_WORKSPACE_ID=...
RENDER_SERVICE_ID=...
```

The API key stays on the FastAPI service and is never returned to the browser.

Check configuration:

```http
GET /api/v1/integrations/render/status
```

Sync recent Render telemetry:

```http
POST /api/v1/integrations/render/sync
Content-Type: application/json

{
  "repository_url": "https://github.com/laksh150806/ForgeAI",
  "lookback_minutes": 60,
  "log_limit": 100,
  "deploy_limit": 20,
  "reconstruct_timeline": true
}
```

This uses Render's free REST API polling path rather than Render workspace webhooks, which
are a paid-plan feature.
