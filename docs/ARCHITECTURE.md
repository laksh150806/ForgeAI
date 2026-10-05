# ForgeAI Architecture

## Product goal

ForgeAI converts a software-engineering task into an auditable workflow:

```
Repository -> Index -> Retrieve -> Investigate -> Plan -> Patch -> Validate -> Report
```

## Initial system boundaries

### Web
Next.js application responsible for repository onboarding, engineering-task input,
agent execution visualization, diffs, validation results, and evaluation metrics.

### API
FastAPI service responsible for authentication boundaries, repository ingestion,
task orchestration, retrieval, model/tool adapters, validation jobs, and persistence.

### Code intelligence
Source-aware retrieval subsystem using AST/symbol extraction, lexical ranking, and
optional embedding-based semantic reranking. Retrieval degrades safely to lexical mode
when no embedding provider is configured.

### Agent runtime
The first investigation stage is evidence-driven: it consumes ranked repository evidence,
produces a bounded-confidence hypothesis, and recommends verification steps. Later stages
will extend this into planning, patching, validation, and review while preserving explicit
state transitions and observable inputs/outputs.

### Validation sandbox
Planned isolated environment for dependency installation, test execution, linting,
type checks, security scans, and regression verification.

## Design principles

1. Evidence before generation.
2. Every proposed code change must be attributable to repository context.
3. No autonomous write to a repository without validation and an approval boundary.
4. Model providers remain swappable.
5. Agent execution must be observable and benchmarkable.
6. ForgeAI should fail safely when repository context or validation is insufficient.

## MVP milestones

1. Repository URL ingestion.
2. Repository file inventory.
3. Code chunking and index.
4. Task-to-file retrieval.
5. Structured investigation report.
6. Patch proposal and diff preview.
7. Validation execution.
8. Final engineering report.
