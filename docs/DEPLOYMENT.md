# ForgeAI Production Deployment

ForgeAI runs as two Render web services with optional **Supabase Free Postgres** for
persistent execution traces.

## Zero-cost production stack

- Frontend: Render Free web service
- API: Render Free web service
- Persistent traces: Supabase Free Postgres
- Public repository ingestion: shallow Git checkout, no GitHub API key required
- AI model providers: optional; the core product works without a paid API key

Supabase Free currently includes a full Postgres database with a 500 MB database-size
quota. Free-plan terms can change over time, so ForgeAI keeps persistence optional and
degrades safely to in-memory trace history if `DATABASE_URL` is absent.

## Services

### API
- Runtime: Python
- Region: Singapore
- Build: `cd apps/api && pip install -r requirements.txt`
- Start: `cd apps/api && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health: `/health`
- Readiness: `/ready`

### Web
- Runtime: Node
- Region: Singapore
- Build: `cd apps/web && npm install && npm run build`
- Start: `cd apps/web && npm run start -- -p $PORT`

## Supabase Free setup

1. Create a Supabase project on the Free plan.
2. In the Supabase project dashboard, click **Connect**.
3. Choose the **Shared Pooler → Session mode** connection string.
   - Session mode uses port `5432`.
   - It is appropriate for a long-running Render API service.
   - It works over IPv4 on the Free plan.
4. Copy the connection string.
5. Replace `[YOUR-PASSWORD]` with the database password you created.
6. Add the complete connection string to Render → `forgeai-api` → Environment:
   ```
   DATABASE_URL=postgresql://...
   ```
7. Save the environment changes and redeploy the API.

Do not put the database password or connection string in GitHub, README files, screenshots,
or chat messages. ForgeAI automatically adds `sslmode=require` for Supabase URLs when the
connection string does not already specify an SSL mode.

## Required environment

API:
- `FORGEAI_ENV=production`
- `CORS_ORIGINS=https://<web-service>.onrender.com`
- `DATABASE_URL=<Supabase shared session pooler URL>` for durable trace history
- `GITHUB_TOKEN` only if private repositories / validated PR writes are needed
- model keys are optional

Web:
- `NEXT_PUBLIC_API_URL=https://<api-service>.onrender.com`

## Persistence behavior

When `DATABASE_URL` is configured:
- ForgeAI creates the `forgeai_runs` table automatically.
- workflow traces survive API redeploys/restarts.
- `GET /api/v1/runs/recent` reads from Supabase Postgres.

When `DATABASE_URL` is absent:
- ForgeAI still works.
- the latest 50 traces remain in memory.
- trace history resets when the API restarts.

## Validation limitation on Render

ForgeAI's strongest sandbox validation path requires access to a Docker daemon. Standard
Render native web services do not expose Docker-in-Docker. In that environment ForgeAI
falls back to non-executing Git diff validation and deliberately keeps the PR gate closed.

For full production PR automation, run the validation worker on infrastructure that
supports an isolated container runtime, or attach a dedicated sandbox execution service.

## Deployment verification

After changing `DATABASE_URL`:
1. `GET /health` should return `status=ok`.
2. `GET /ready` should return `status=ready`.
3. Run a workflow using `POST /api/v1/runs/execute`.
4. Redeploy/restart the API.
5. Confirm the same run still appears in `GET /api/v1/runs/recent`.
