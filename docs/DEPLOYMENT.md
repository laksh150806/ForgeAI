# ForgeAI Production Deployment

ForgeAI is deployed as two Render web services plus an optional Render Postgres database.

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

## Required environment

API:
- `FORGEAI_ENV=production`
- `CORS_ORIGINS=https://<web-service>.onrender.com`
- `DATABASE_URL=<Render internal Postgres URL>` for trace persistence
- `GITHUB_TOKEN` for private repositories and validated PR creation
- `OPENAI_API_KEY` or `LLM_API_KEY` for semantic retrieval / patch generation

Web:
- `NEXT_PUBLIC_API_URL=https://<api-service>.onrender.com`

## Validation limitation on Render

ForgeAI's strongest sandbox validation path requires access to a Docker daemon. Standard
Render native web services do not expose Docker-in-Docker. In that environment ForgeAI
falls back to non-executing Git diff validation and deliberately keeps the PR gate closed.

For full production PR automation, run the validation worker on infrastructure that
supports an isolated container runtime, or attach a dedicated sandbox execution service.
This limitation is intentional and is surfaced in the product instead of being hidden.

## Deployment verification

After a deploy:
1. `GET /health` should return status `ok`.
2. `GET /ready` should return status `ready`.
3. Open the web service and run repository analysis.
4. Run the benchmark seed set.
5. Confirm persisted workflow runs appear under `GET /api/v1/runs/recent` when Postgres is configured.
