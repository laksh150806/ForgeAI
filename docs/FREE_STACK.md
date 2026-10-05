# ForgeAI Zero-Cost Stack

ForgeAI has no mandatory paid dependency.

## Current zero-cost architecture

| Layer | Provider | Cost requirement |
| --- | --- | --- |
| Frontend | Render Free | $0 while within free-tier limits |
| API | Render Free | $0 while within free-tier limits |
| Persistent traces | Supabase Free Postgres | $0 while within free-tier limits |
| Public GitHub repositories | Git clone | No token required |
| Retrieval | Lexical + structural | No model API required |
| Benchmarking | Built in | No paid dependency |
| CI/CD | GitHub Actions | Uses repository plan limits |

## Optional integrations

These are not required for the core live product:

- `GITHUB_TOKEN`: private repositories and write/PR automation.
- Model provider key: semantic reranking and model-generated patches.
- Dedicated sandbox infrastructure: full isolated test execution.

ForgeAI intentionally degrades safely when an optional integration is unavailable.

## Supabase Free notes

The Free plan currently provides two free projects and a 500 MB database-size quota per
project. It can pause inactive projects depending on Supabase's current free-plan policy,
so "free forever" should be interpreted as **no mandatory paid dependency**, not a
guarantee that a third-party provider will never change its free tier.

ForgeAI uses ordinary Postgres and can be moved to any compatible Postgres provider later
without changing the application data model.
