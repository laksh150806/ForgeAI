from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.code_intelligence import router as code_intelligence_router
from app.routes.investigations import router as investigations_router
from app.routes.evaluation import router as evaluation_router
from app.routes.planning import router as planning_router
from app.routes.pull_requests import router as pull_requests_router
from app.routes.repositories import router as repositories_router
from app.routes.runs import router as runs_router
from app.routes.validation import router as validation_router

app = FastAPI(
    title="ForgeAI API",
    version="0.7.0",
    description="Autonomous software engineering and incident intelligence platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repositories_router)
app.include_router(code_intelligence_router)
app.include_router(investigations_router)
app.include_router(evaluation_router)
app.include_router(planning_router)
app.include_router(pull_requests_router)
app.include_router(validation_router)
app.include_router(runs_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "forgeai-api"}


@app.get("/api/v1/status")
def status() -> dict[str, str]:
    return {
        "product": "ForgeAI",
        "phase": "evaluation-benchmarks",
        "capability": "gold-labeled retrieval and end-to-end agent evaluation",
    }
