from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath

from app.schemas.repository import (
    LanguageStat,
    RepositoryAnalysisResponse,
    RepositoryFile,
    RepositorySummary,
)
from app.services.github_client import GitHubClient, parse_github_repository_url


EXTENSION_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".h": "C/C++",
    ".cc": "C++",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
}

IGNORED_DIRECTORIES = {
    ".git",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "target",
}

IGNORED_FILE_NAMES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
}

IMPORTANT_FILE_NAMES = {
    "README.md",
    "README",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    ".env.example",
}

SOURCE_LANGUAGES = {
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "C",
    "C/C++",
    "C++",
    "C#",
    "Go",
    "Rust",
    "Ruby",
    "PHP",
    "Swift",
    "Kotlin",
    "Scala",
    "SQL",
    "Shell",
    "Vue",
    "Svelte",
    "HTML",
    "CSS",
    "SCSS",
}


def classify_path(path: str, size: int | None = None) -> RepositoryFile:
    pure = PurePosixPath(path)
    parts = set(pure.parts)

    ignored_reason = None
    if parts & IGNORED_DIRECTORIES:
        ignored_reason = "generated_or_dependency_directory"
    elif pure.name in IGNORED_FILE_NAMES:
        ignored_reason = "lockfile"
    elif size is not None and size > 1_000_000:
        ignored_reason = "file_too_large"

    language = EXTENSION_LANGUAGE.get(pure.suffix.lower())

    if pure.name in IMPORTANT_FILE_NAMES:
        kind = "important"
    elif language in SOURCE_LANGUAGES:
        kind = "source"
    elif language:
        kind = "support"
    else:
        kind = "other"

    return RepositoryFile(
        path=path,
        size=size,
        language=language,
        kind=kind,
        ignored=ignored_reason is not None,
        ignore_reason=ignored_reason,
    )


def _language_stats(files: list[RepositoryFile]) -> list[LanguageStat]:
    counts = Counter(
        file.language
        for file in files
        if not file.ignored
        and file.kind == "source"
        and file.language is not None
    )
    total = sum(counts.values())
    if total == 0:
        return []

    return [
        LanguageStat(
            language=language,
            files=count,
            share=round(count / total, 4),
        )
        for language, count in counts.most_common()
    ]


async def analyze_repository(repository_url: str) -> RepositoryAnalysisResponse:
    ref = parse_github_repository_url(repository_url)
    client = GitHubClient()

    try:
        repository = await client.repository(ref)
        default_branch = repository.get("default_branch") or "main"
        commit = await client.commit(ref, default_branch)
        tree_sha = commit["commit"]["tree"]["sha"]
        tree = await client.tree(ref, tree_sha)
    finally:
        await client.close()

    if tree.get("truncated"):
        # Keep the result useful while making the limitation explicit through counts.
        # A paginated contents crawler can be added for very large repositories later.
        pass

    blobs = [item for item in tree.get("tree", []) if item.get("type") == "blob"]
    files = [
        classify_path(item["path"], item.get("size"))
        for item in blobs
        if item.get("path")
    ]

    source_files = sum(
        1 for file in files if file.kind == "source" and not file.ignored
    )
    ignored_files = sum(1 for file in files if file.ignored)
    important_files = [
        file.path
        for file in files
        if file.kind == "important" and not file.ignored
    ][:30]

    summary = RepositorySummary(
        owner=ref.owner,
        name=ref.name,
        full_name=ref.full_name,
        default_branch=default_branch,
        visibility=repository.get("visibility", "public"),
        description=repository.get("description"),
        stars=repository.get("stargazers_count", 0),
        forks=repository.get("forks_count", 0),
        total_files=len(files),
        source_files=source_files,
        ignored_files=ignored_files,
        languages=_language_stats(files),
        important_files=important_files,
    )

    return RepositoryAnalysisResponse(repository=summary, files=files)
