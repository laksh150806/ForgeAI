from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.repositories import router as repositories_router

app = FastAPI(
    title="ForgeAI API",
    version="0.2.0",
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "forgeai-api"}


@app.get("/api/v1/status")
def status() -> dict[str, str]:
    return {
        "product": "ForgeAI",
        "phase": "repository-intelligence",
        "capability": "GitHub repository analysis",
    }
