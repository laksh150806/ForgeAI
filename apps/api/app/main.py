from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ForgeAI API",
    version="0.1.0",
    description="Autonomous software engineering and incident intelligence platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "forgeai-api"}


@app.get("/api/v1/status")
def status() -> dict[str, str]:
    return {
        "product": "ForgeAI",
        "phase": "foundation",
        "capability": "repository intelligence bootstrap",
    }
