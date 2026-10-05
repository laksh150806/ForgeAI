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
Planned subsystem using Tree-sitter/AST parsing plus semantic and lexical retrieval.

### Agent runtime
Planned state-machine workflow with explicit stages instead of a single open-ended
LLM loop. Each stage must record inputs, outputs, tool calls, latency, and failures.

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
