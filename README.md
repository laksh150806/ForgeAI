# ForgeAI

**Autonomous AI Software Engineering & Incident Intelligence Platform**

ForgeAI is a production-oriented AI engineering platform designed to understand software repositories, investigate engineering tasks and incidents, propose code changes, validate them, and produce an auditable engineering report.

## Vision

ForgeAI is not a generic coding chatbot. The target workflow is:

```
Repository
   ↓
Code Intelligence
   ↓
Task / Incident Investigation
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

**Phase 1 — Foundation**

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
- [ ] GitHub repository ingestion
- [ ] Repository file inventory
- [ ] AST-aware code parsing
- [ ] Semantic + lexical retrieval
- [ ] Task-to-file investigation agent
- [ ] Structured engineering plan
- [ ] Patch/diff generation
- [ ] Sandboxed validation
- [ ] Execution traces and metrics
- [ ] Human-approved GitHub PR creation
- [ ] Evaluation benchmark suite

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

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the current architecture.
