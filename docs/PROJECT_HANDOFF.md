# ForgeAI — Project Handoff / Source of Truth

> Purpose: exhaustive continuity document for starting a fresh ChatGPT conversation without losing project state.
> Last updated: 2026-10-10.
> Never place secrets, tokens, passwords, or private connection strings in this file.

## 1. Project identity

**Project:** ForgeAI  
**Owner GitHub:** laksh150806  
**Repository:** https://github.com/laksh150806/ForgeAI  
**Current product direction:** Autonomous Production Debugging & Remediation Engine

ForgeAI started as an autonomous software-engineering platform but was deliberately pivoted away from generic "AI coding assistant / CodeRabbit-like" positioning. Its differentiator is now:

```text
production failure
  -> runtime telemetry
  -> deploy / commit correlation
  -> suspect regression
  -> changed-symbol / runtime-path localization
  -> dependency + call graph blast radius
  -> code-level root cause
  -> engineering plan
  -> patch
  -> validation
  -> human approval
  -> GitHub PR
```

The core should remain **provider-agnostic**. Render is only adapter #1; Vercel is adapter #2.

## 2. Live production URLs

- Web: https://forgeai-web-irot.onrender.com
- API: https://forgeai-api-ok42.onrender.com
- GitHub repo: https://github.com/laksh150806/ForgeAI

## 3. Current infrastructure

### Render

Workspace ID:
`tea-daao6grtqb8s73ftloe0`

API service:
- name: forgeai-api
- service ID: `srv-db1qoj49v7es738q3u5g`
- region: Singapore
- runtime: Python
- production Python target: **3.12.14**

Web service:
- name: forgeai-web
- service ID: `srv-db1qolajnfac73e8ev5g`
- region: Singapore
- runtime: Node/Next.js

Important operational lesson:
- Render previously defaulted to Python 3.14.3, causing `pydantic-core` / maturin / Rust build failures.
- The repo now pins Python at the **repo root** using `.python-version` = `3.12.14`.
- Do not place the pin only in `apps/api/.python-version`; Render chooses runtime before `cd apps/api`.
- `PYTHON_VERSION` should remain `3.12.14` if present in Render.
- A prior human mistake accidentally put a PostgreSQL URL into `PYTHON_VERSION`; this was fixed.
- Avoid unnecessary Render environment mutations because they previously caused confusing deploy loops.

### Supabase

Organization ID:
`tgckrzadnkjbucrjbsvn`

Project ID/ref:
`ibacapyudtsxjcohfumk`

Project region:
`ap-northeast-1`

Database:
- PostgreSQL 17
- Free plan
- uses shared Supavisor/session pooler for IPv4 access from Render

Current durable tables:
- `public.forgeai_runs`
- `public.forgeai_telemetry_events`

Security posture:
- RLS enabled
- no public anon/authenticated table policy by design
- backend connects directly to Postgres
- `anon` / `authenticated` table access was revoked
- Supabase advisors only showed expected INFO-level notices (for example RLS without policy and fresh unused indexes)

Do not expose:
- database password
- full `DATABASE_URL`
- service role keys

## 4. Important environment variable names

### API / Render

Core:
- `FORGEAI_ENV`
- `CORS_ORIGINS`
- `DATABASE_URL`
- `PYTHON_VERSION`

Optional model capability:
- `OPENAI_API_KEY`
- `LLM_API_KEY`
- model defaults currently use `gpt-6-luna` in planning code

GitHub writes/private repositories:
- `GITHUB_TOKEN`

Render adapter:
- `RENDER_API_KEY`
- `RENDER_WORKSPACE_ID`
- `RENDER_SERVICE_ID`

Current non-secret Render adapter IDs:
- `RENDER_WORKSPACE_ID=tea-daao6grtqb8s73ftloe0`
- `RENDER_SERVICE_ID=srv-db1qoj49v7es738q3u5g`

Vercel adapter:
- `VERCEL_TOKEN`
- `VERCEL_PROJECT_ID`
- `VERCEL_TEAM_ID` (optional for personal scope)

Sentry adapter:
- `SENTRY_AUTH_TOKEN`
- `SENTRY_ORG`
- `SENTRY_PROJECT`
- `SENTRY_ENVIRONMENT` (optional)

Web:
- `NEXT_PUBLIC_API_URL`

Never write secret values into GitHub, docs, chat handoff files, or frontend code.

## 5. Deployment / database incident history worth remembering

### Supabase migration issue

The first Supabase connection attempts failed because a password contained an `@` and the URI was malformed. Render error included a hostname that incorrectly contained part of the password before the actual pooler hostname.

Correct principles:
- if URI-style, special password characters must be percent-encoded
- alternatively use valid libpq keyword conninfo
- for Supabase pooled connection, SSL must be required
- shared pooler port 5432 is appropriate for persistent Render API on free IPv4 path

After the user corrected the Render `DATABASE_URL`, production persistence was verified with real rows in `forgeai_runs`.

### Python deploy loop

A second issue was caused by `PYTHON_VERSION` being overwritten with the DB connection string. Once corrected:
- `PYTHON_VERSION=3.12.14`
- root `.python-version=3.12.14`
- `DATABASE_URL` kept separately
the loop was resolved.

## 6. Development history / major PRs

### Phase 1 — foundation
PR #1
- FastAPI foundation
- Next.js web foundation
- health/status
- docs/env/gitignore

### Phase 2 — repository intelligence
PR #2
- GitHub repository metadata/file inventory
- repository schemas/services/routes/tests/UI
- endpoint: `POST /api/v1/repositories/analyze`

### Phase 3 — code intelligence + lexical retrieval
PR #3
- Python AST symbol extraction
- JS/TS regex symbol extraction
- tokenization/chunking
- TF-IDF-ish lexical ranking
- path/symbol boosts
- endpoint: `POST /api/v1/code/search`

### Phase 4 — hybrid retrieval + investigation
PR #4
- optional OpenAI embeddings
- lexical + semantic hybrid scoring
- investigation agent
- evidence / rationale / confidence
- endpoint: `POST /api/v1/investigations/run`

### Phase 5 — planning + patch generation
PR #5
- deterministic engineering plans
- optional LLM patch generation
- conservative strict JSON patch output
- existing-files-only
- endpoint: `POST /api/v1/plans/generate`

### Phase 6 — sandbox validation
PR #6
- temp checkout
- git apply checks
- Docker safety boundary design
- Python/Node validation commands
- if Docker unavailable, validation remains non-executing and PR gate stays closed

Important production limitation:
Render native service does **not** provide Docker-in-Docker, so strong sandbox execution is not available live. ForgeAI intentionally fails closed instead of pretending validation succeeded.

### Phase 7 — execution traces
PR #7
- `POST /api/v1/runs/execute`
- stage timing/status/details/errors
- run IDs + metrics
- trace UI

### Phase 8 — human-approved GitHub PR creation
PR #8
- `POST /api/v1/pull-requests/create`
- requires `approved=true`
- fresh server validation
- creates branch + commits + PR
- never writes directly to default branch

Known limitations:
- existing files only
- one commit per file (not atomic)
- base SHA is not fully pinned against TOCTOU
- uses env token, not GitHub App
- partial branch can exist on mid-write failure

### Phase 9 — evaluation benchmark
PR #9
- benchmark API
- Top-1, Recall@K, MRR, symbol accuracy, latency
- endpoint: `POST /api/v1/evaluation/benchmark`
- seed benchmark in `benchmarks/forgeai.json`

Seed cases:
1. GitHub URL validation
2. sandbox patch validation
3. PR approval gate

Important honesty requirement:
- benchmark is tiny/self-repo (3 cases)
- do not present it as a broad SWE benchmark

### Phase 10 — production hardening
PR #10
- env CORS
- `/health`
- `/ready`
- Postgres trace persistence skeleton
- `/runs/recent`
- deployment docs
- Render API + web deployment

### UI / smoke / public repo hardening
PRs #11–#20 included:
- polished UI
- benchmark seed endpoint
- external live smoke workflow
- public repo checkout fallback via shallow git clone
- removed dependence on anonymous GitHub REST quota for public repo indexing/planning
- fixed Generate Plan 429 caused by planning context still using GitHub REST
- retrieval ranking v2 aliases/structural boosts/test downranking
- persistent trace history + trace drilldown endpoint/UI

### Supabase free persistence migration
PR #22
- provider-agnostic Postgres trace store
- Supabase SSL handling
- deployment/free-stack docs

PR #23
- root Python version pin `.python-version=3.12.14`

### Responsive UI
PR #24
- fluid mobile/tablet/desktop layout
- no page horizontal overflow
- long path/symbol wrapping
- responsive grids
- mobile full-width actions
- breakpoint hierarchy for phone/tablet/desktop

### Production incident correlation
PR #25
- new endpoint: `POST /api/v1/incidents/correlate`
- runtime symptoms/error/stack/log evidence
- optional deploy SHA
- bounded recent git history inspection
- scores recent commits by:
  - runtime-term overlap
  - direct changed-file mentions
  - overlap with retrieved code evidence
  - explicit deploy SHA
  - bounded recency prior
- returns primary suspect commit + confidence + reasons
- cross-checks with normal code retrieval/investigation
- new incident correlation UI

PR #26
- external production smoke coverage for incident correlation

### Persistent telemetry + timeline reconstruction
PR #27
- `POST /api/v1/telemetry/events`
- `POST /api/v1/telemetry/timeline`
- persistent `forgeai_telemetry_events`
- first-failure detection
- nearest preceding deploy selection
- surrounding telemetry converted into runtime evidence
- timeline -> regression correlation
- responsive telemetry UI

PR #28
- live telemetry smoke:
  - ingest deploy + warning + error
  - reconstruct timeline
  - assert nearest deploy
  - assert correlation

Smoke-data bug:
persisted smoke telemetry originally reused one service name and polluted later tests.
Fixed by using a unique service per GitHub Actions run.

### Automatic Render adapter
PR #29
- `GET /api/v1/integrations/render/status`
- `POST /api/v1/integrations/render/sync`
- pulls Render deploy history + logs
- normalizes into ForgeAI telemetry
- deterministic event IDs
- persists to Supabase
- optional timeline reconstruction
- API key stays server-side
- UI sync control

Render adapter production verification:
- real adapter status configured
- real sync pulled:
  - 5 deploy events
  - 100 Render log events
  - 105 accepted events
  - storage = postgres
- Supabase was queried directly and contained real `source='render'` rows

PR #30
- live Render adapter smoke coverage

PR #31
- improved live-smoke diagnostics so upstream adapter errors print JSON body before failing

PR #32
- isolated telemetry smoke data per run

PR #33
- fixed Render deploy polling:
  - Render rejected `createdAfter` in our deploy-list request with HTTP 400
  - ForgeAI now fetches a bounded deploy list and filters locally

After PR #33, real Render adapter sync passed.

### Multi-provider runtime architecture + Vercel
PR #34
- shared `runtime_provider.py` ingestion/persistence/timeline boundary
- Render refactored through shared provider pipeline
- Vercel adapter added:
  - `GET /api/v1/integrations/vercel/status`
  - `POST /api/v1/integrations/vercel/sync`
  - deployment history
  - build/deployment events
  - Git SHA mapping
  - deterministic event IDs
  - Supabase persistence
  - optional timeline reconstruction
- provider-aware UI cards for Render + Vercel
- Vercel normalization tests
- architecture/docs updated

Vercel limitation:
- normal Hobby REST access should **not** be described as full runtime-log export
- runtime errors can enter ForgeAI through generic telemetry
- Vercel Log Drains can be adapted later for users with that capability

PR #35
- production smoke check for Vercel adapter status
- verifies integration surface without requiring a configured Vercel project

At the time of this handoff:
- user has **no Vercel deployments**
- therefore Vercel is implemented but not connected to a real Vercel project/token
- do not waste time asking user to create a Vercel deploy just for testing unless they want to

### Dependency / call graph + blast-radius analysis
PR #37
- endpoint: `POST /api/v1/impact/analyze`
- Python AST symbols/imports/approximate calls
- JS/TS regex symbols/imports/approximate calls
- directed `imports`, `calls`, and `references` edges
- Git diff hunk -> changed symbol/module mapping
- runtime/error/stack text -> graph-node mapping
- bounded upstream callers, downstream dependencies, and affected route/API entrypoints
- evidence paths, blast-radius score, confidence, and explanations
- graph evidence feeds incident-correlation scoring
- responsive web panel for changed symbols, affected entrypoints, and evidence paths
- API version 0.15.0

PR #38
- deterministic production smoke for `/api/v1/impact/analyze`
- incident-correlation smoke updated for `+blast-radius` mode

PR #39
- separate graph regression benchmark: `GET /api/v1/evaluation/impact-seed`
- benchmark file: `benchmarks/forgeai-impact.json`
- original 3-case retrieval seed remains separate for historical comparability
- 2 pinned ForgeAI self-repo impact cases:
  1. `analyze_impact` -> entrypoint `analyze`
  2. `correlate_incident` -> entrypoint `correlate`
- graph metrics:
  - changed-symbol accuracy
  - runtime-symbol accuracy
  - affected-entrypoint accuracy
  - average blast-radius score

PR #40
- prioritizes runtime-relevant changed symbols before response truncation
- added regression coverage for large changed-symbol sets

PR #41
- materializes the selected historical Git commit before source scanning
- prevents old diff line numbers from being mapped against current `main`

PR #42
- hydrates exact unified-zero diffs per changed source file
- prevents the bounded combined history patch from hiding later file hunks in large commits
- final production fix for historical changed-symbol mapping

Final production API commit for this phase:
`d9731b5aa7c05554eff8fd4c493b220311076551`

### Sentry runtime adapter
PR #44
- API version 0.16.0
- endpoints:
  - `GET /api/v1/integrations/sentry/status`
  - `POST /api/v1/integrations/sentry/sync`
- server-side Bearer auth via `SENTRY_AUTH_TOKEN`
- project-scoped recent error-event polling with bounded pagination and full event bodies
- normalizes Sentry exception data into the shared ForgeAI `TelemetryEvent` model:
  - source = `sentry`
  - error severity/type
  - project/service
  - title/message
  - exception stack frames
  - issue/event IDs
  - environment
  - release metadata
- conservatively extracts Git-like release hashes into `deploy_sha` when present
- deterministic event IDs
- reuses shared provider persistence, Supabase storage, timeline reconstruction, incident correlation, and blast-radius flow
- responsive Sentry provider card added alongside Render/Vercel
- runtime provider grid changed to auto-fit instead of a fixed two-column desktop layout
- deterministic tests cover stack normalization, release/SHA extraction, event IDs, and pagination cursor parsing
- production smoke verifies the Sentry status endpoint without requiring a configured Sentry account

Current Sentry production state:
- adapter implementation is deployed live on commit `c85e84361453e8c7067641abd850075191ccdc96`
- Sentry status endpoint is production verified
- no real Sentry token/project is configured yet, so real Sentry sync has **not** been production-tested
- do not ask the user to paste a Sentry token into chat; configure it server-side only if/when they choose to connect Sentry



## 7. Latest production verification

Latest production verification, 2026-10-10:
- Sentry adapter PR #44 API + web are live on commit `c85e84361453e8c7067641abd850075191ccdc96`
- post-Sentry live-smoke run #29 completed successfully after rerun against the stable deployed revision
- Sentry adapter status ✅
- blast-radius phase remains verified from PR #42 commit `d9731b5aa7c05554eff8fd4c493b220311076551`
- final GitHub Actions live-smoke run #28 completed successfully after the production revision was live
- the same production smoke passed:
  - API health ✅
  - database readiness ✅
  - original 3-case retrieval seed ✅
  - 2-case impact regression benchmark ✅
  - Generate Plan ✅
  - direct blast-radius analysis ✅
  - incident correlation with graph evidence ✅
  - telemetry timeline ✅
  - real Render adapter sync ✅
  - Vercel adapter status ✅
  - persistent trace history ✅
  - live web ✅
- final real Render adapter sync in that smoke:
  - 2 deploy events
  - 100 log events
  - 102 accepted events

Operational lesson:
- Render commit-triggered deploys have not always started automatically.
- When needed, use a normal deploy with cache retained and do not mutate environment variables.
- Live-smoke can race Render's zero-downtime traffic swap; verify the target commit is actually live before treating a smoke failure as an application failure.

## 8. Benchmark history

### Original retrieval seed
Exactly 3 ForgeAI self-repo cases:
1. GitHub URL validation
2. sandbox patch validation
3. PR approval gate

Historical post-ranking-v2 clean rerun:
- Top-1: 66.67%
- Recall@3: 100%
- MRR: 0.8333
- symbol hit: 100%
- avg ranking latency: ~99.67ms

Earlier later-measured smoke:
- Top-1: 66.67%
- Recall@3: 100%
- MRR: 0.7778
- symbol accuracy: 100%
- avg latency: 137ms

Latest production smoke on 2026-10-10:
- Top-1: 66.67%
- Recall@3: 100%
- MRR: 0.8333
- symbol accuracy: 100%
- avg ranking latency: 170.0ms

### Impact regression seed
Separate 2-case pinned ForgeAI self-repo benchmark:
- pinned regression commit: `3dd89c8b4ebebf24a70aef672f8c13846853eab8`
- changed-symbol accuracy: **100%**
- runtime-symbol accuracy: **100%**
- affected-entrypoint accuracy: **100%**
- average blast-radius score: **82.0**

Per-case blast-radius scores:
- `analyze_impact`: 80.0, confidence 0.80
- `correlate_incident`: 84.0, confidence 0.83

The impact benchmark also emits normal retrieval metrics, but its purpose is graph/regression localization.
Do not combine the 3 retrieval cases and 2 impact cases into a claim of broad benchmark coverage.
Both suites are tiny/self-repo; never present them as a general SWE benchmark.

## 9. Current functional capabilities

### Repository / code intelligence
- public GitHub repository checkout
- source classification / ignore noise
- Python AST symbols
- JS/TS regex symbols
- lexical structural retrieval
- optional semantic rerank if model key is configured
- path/symbol/query-alias ranking

### Investigation
- evidence-based hypothesis
- rationale
- confidence
- suggested next actions

### Planning / patching
- deterministic engineering plan
- optional model-generated patch
- patch preview

### Validation
- git patch applicability
- Docker isolation design
- live Render environment intentionally cannot execute strong Docker sandbox
- PR gate stays closed when strong validation is unavailable

### GitHub PR flow
- explicit human approval required
- branch creation
- file updates
- PR creation

### Observability
- workflow stage traces
- recent trace history
- Supabase durable persistence
- trace drilldown endpoint/UI

### Evaluation
- original 3-case retrieval seed benchmark
- separate 2-case graph regression benchmark
- graph metrics for changed symbol, runtime symbol, affected entrypoint, and blast-radius score
- live smoke CI

### Incident intelligence
- runtime evidence -> suspect commit
- deploy SHA correlation
- recent diff inspection
- retrieval cross-check
- first failure detection
- nearest preceding deploy
- production timeline reconstruction
- Git diff -> changed-symbol mapping
- runtime / stack evidence -> graph-node mapping
- bounded upstream/downstream dependency traversal
- affected route/API entrypoint identification
- blast-radius score + evidence paths
- graph evidence feeds incident-correlation confidence

### Runtime providers
- generic telemetry ingestion
- Render automatic adapter (real sync production verified)
- Vercel adapter (implemented, status production verified, not connected to real project yet)
- Sentry adapter (implemented and status production verified; real sync not yet configured/tested)

## 10. Current limitations / do not misrepresent

1. No mandatory paid model dependency.
2. If no OpenAI/LLM key:
   - semantic embeddings are not active
   - patch generation can return `model_unavailable`
   - lexical structural retrieval still works.
3. If no GitHub token:
   - private repos unavailable
   - real PR writes unavailable
   - public clone path works.
4. Strong sandbox execution unavailable on Render because no Docker-in-Docker.
5. Vercel runtime logs are not fully available through the normal Hobby REST integration; use generic telemetry or future Log Drain support.
6. Call/dependency graph analysis is static and approximate:
   - Python uses AST symbols/imports/calls
   - JS/TS uses regex/approximate symbols/imports/calls
   - dynamic dispatch, reflection, generated code, runtime-only bindings, and framework magic can be missed.
7. Graph construction is per request and bounded; there is not yet a persistent repository-wide graph store.
8. Impact traversal and response lists are bounded/capped.
9. Sentry adapter is implemented, but no real Sentry project/token is configured yet; only the status surface is production verified.
10. Sentry release/commit mapping is intentionally conservative and remains unknown when release metadata does not contain a Git-like hash.
11. Railway adapter is **not implemented yet**.
12. AWS/GCP/Azure/Kubernetes adapters are **not implemented yet**.
13. Both benchmark suites are tiny and self-repo.
14. Model token/cost persistence is not implemented.
15. GitHub PR writer remains non-atomic across multiple file commits.
16. ForgeAI should not be marketed as "CodeRabbit clone"; product differentiation is production debugging/remediation.

## 11. Product positioning

Avoid generic:
> AI coding assistant that understands your repo and opens PRs

Prefer:
> ForgeAI is an autonomous production debugging and remediation engine that correlates runtime failures with deploys and code changes, localizes the likely regression, builds an evidence-backed root-cause hypothesis, and drives the issue toward a validated human-approved fix.

Strong demo sentence:
> "Production checkout latency spiked after deploy 8f3a2c. ForgeAI reconstructs the incident window, identifies the nearest deploy, maps it to changed code, ranks the likely regression, and prepares the fix path."

## 12. UI principles

The user explicitly cares about responsive/mobile usability.

Do not hardcode UI for one screen.
Use:
- fluid widths
- clamp() typography/spacing
- shrink-safe grid/flex children
- wrap long paths/symbols
- phone -> tablet -> desktop layout adaptation
- avoid horizontal overflow
- full-width actions on small screens

PR #24 established these rules.

## 13. User working style / preferences

- Wants hands-on implementation, not abstract advice.
- Frequently says "do it" and expects direct execution when tools permit.
- Prefer GitHub connector for repo work.
- Prefer Render connector for deploy/log/service work.
- Prefer Supabase connector for DB migrations/queries.
- Avoid unnecessary questions.
- On phone, give detailed manual steps only when unavoidable.
- Never ask user to paste secrets into chat.
- Never expose secret values found in connected services.
- For long tasks, give short progress updates every few tool calls.
- Do not redo broad audits when a narrow production verification is enough.

## 14. What not to do

- Do not mutate Render env vars unnecessarily.
- Do not expose `DATABASE_URL`, Render API key, Vercel token, GitHub token, DB password, or model keys.
- Do not claim Docker sandbox validation is active on Render.
- Do not call the tiny 3-case retrieval seed or 2-case impact seed a general benchmark.
- Do not claim Vercel runtime logs are available on Hobby if they are not.
- Do not claim real Sentry sync is production verified until a Sentry project/token is actually configured and synced.
- Do not make ForgeAI Render-specific.
- Do not spend time adding provider adapters merely for breadth if the next feature adds more debugging intelligence.

## 15. Recommended next phase

The next highest-value engineering phase is:

# GitHub Actions / Deployments adapter

Goal:
Add CI/CD context to incident correlation so ForgeAI can distinguish a source-code regression from a failed build, workflow change, or deployment transition:

> runtime failure -> deployment/release -> GitHub deployment/workflow run -> commit -> changed symbol -> blast radius -> remediation path

Keep GitHub-specific polling at the ingestion boundary and normalize useful events into the existing ForgeAI telemetry/runtime-provider model.

Suggested implementation sequence:
1. Reuse server-side `GITHUB_TOKEN` when configured; keep public-repo reads available where GitHub permits.
2. Add GitHub Actions/Deployments status surface.
3. Poll bounded recent:
   - deployments + deployment statuses
   - workflow runs for the repository/default branch
   - failed job/step summaries where practical
4. Normalize into ForgeAI telemetry:
   - source = `github`
   - event types such as `deploy`, `ci_failure`, `workflow`
   - commit/deploy SHA
   - workflow/deployment identifiers
   - status/conclusion
   - relevant URLs/metadata
5. Feed normalized deployment/CI evidence through timeline reconstruction and incident correlation.
6. Add:
   - `GET /api/v1/integrations/github-runtime/status`
   - `POST /api/v1/integrations/github-runtime/sync`
7. Add responsive provider UI.
8. Add deterministic normalization tests.
9. Add live status smoke; only make authenticated/private-repo behavior conditional on configuration.
10. Keep scope bounded so this improves debugging intelligence rather than becoming generic CI monitoring.

After GitHub Actions/Deployments, likely priorities:
- Railway adapter
- richer incident memory / repeated-regression detection
- persistent/cached repository graph for larger codebases

## 16. Fresh-chat bootstrap instruction

At the beginning of a new chat, tell ChatGPT:

> We are continuing ForgeAI. Read `docs/PROJECT_HANDOFF.md` from `laksh150806/ForgeAI` first and treat it as the project source of truth. Do not repeat completed phases. Verify live state only where needed. Continue with the "Recommended next phase" unless I ask for something else.

