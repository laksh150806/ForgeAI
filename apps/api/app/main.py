import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.routes.code_intelligence import router as code_intelligence_router
from app.routes.investigations import router as investigations_router
from app.routes.incidents import router as incidents_router
from app.routes.impact import router as impact_router
from app.routes.integrations import router as integrations_router
from app.routes.vercel_integration import router as vercel_integration_router
from app.routes.sentry_integration import router as sentry_integration_router
from app.routes.evaluation import router as evaluation_router
from app.routes.planning import router as planning_router
from app.routes.pull_requests import router as pull_requests_router
from app.routes.repositories import router as repositories_router
from app.routes.runs import router as runs_router
from app.routes.telemetry import router as telemetry_router
from app.routes.validation import router as validation_router
from app.services.trace_store import database_ready

app = FastAPI(
    title="ForgeAI API",
    version="0.16.0",
    description="Autonomous software engineering and incident intelligence platform.",
)

cors_origins = [
    item.strip()
    for item in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if item.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repositories_router)
app.include_router(code_intelligence_router)
app.include_router(investigations_router)
app.include_router(incidents_router)
app.include_router(impact_router)
app.include_router(integrations_router)
app.include_router(vercel_integration_router)
app.include_router(sentry_integration_router)
app.include_router(evaluation_router)
app.include_router(planning_router)
app.include_router(pull_requests_router)
app.include_router(validation_router)
app.include_router(runs_router)
app.include_router(telemetry_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "forgeai-api"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    if not await database_ready():
        raise HTTPException(
            status_code=503,
            detail="ForgeAI API is running but its configured database is unavailable.",
        )
    return {"status": "ready", "service": "forgeai-api"}


@app.get("/api/v1/status")
def status() -> dict[str, str]:
    return {
        "product": "ForgeAI",
        "phase": "sentry-runtime-adapter",
        "capability": "provider-agnostic runtime telemetry with Render, Vercel, and Sentry adapters plus blast-radius analysis",
    }
