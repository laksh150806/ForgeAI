from __future__ import annotations

import ast
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.schemas.code_intelligence import CodeEvidence, CodeSearchResponse, CodeSymbol
from app.services.github_client import GitHubClient, GitHubRepositoryRef, parse_github_repository_url
from app.services.repository_intelligence import classify_path


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")
JS_SYMBOL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class|interface|type|const|let|var)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)

STOPWORDS = {
    "the","and","for","with","that","this","from","when","where","into","does","fail",
    "fails","failing","error","issue","bug","fix","using","used","use","after","before",
    "should","could","would","have","has","had","are","was","were","its","our","your",
}


@dataclass
class CodeChunk:
    path: str
    language: str | None
    text: str
    symbols: list[CodeSymbol]
    tokens: list[str]


def normalize_tokens(text: str) -> list[str]:
    tokens = [token.lower() for token in TOKEN_RE.findall(text)]
    expanded: list[str] = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        expanded.append(token)
        parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", token).replace("_", " ").split()
        expanded.extend(part.lower() for part in parts if len(part) > 1 and part.lower() not in STOPWORDS)
    return expanded


def extract_python_symbols(source: str) -> list[CodeSymbol]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    symbols: list[CodeSymbol] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(
                CodeSymbol(
                    name=node.name,
                    kind="class" if isinstance(node, ast.ClassDef) else "function",
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", None),
                )
            )
    return sorted(symbols, key=lambda item: item.line_start)


def extract_js_symbols(source: str) -> list[CodeSymbol]:
    symbols: list[CodeSymbol] = []
    lines = source.splitlines()
    for match in JS_SYMBOL_RE.finditer(source):
        line = source.count("\n", 0, match.start()) + 1
        line_text = lines[line - 1] if line <= len(lines) else ""
        kind = "class" if "class " in line_text else "symbol"
        symbols.append(CodeSymbol(name=match.group(1), kind=kind, line_start=line))
    return symbols


def extract_symbols(source: str, language: str | None) -> list[CodeSymbol]:
    if language == "Python":
        return extract_python_symbols(source)
    if language in {"JavaScript", "TypeScript", "Vue", "Svelte"}:
        return extract_js_symbols(source)
    return []


def chunk_source(path: str, source: str, language: str | None, max_lines: int = 90) -> list[CodeChunk]:
    lines = source.splitlines()
    symbols = extract_symbols(source, language)

    if not lines:
        return []

    chunks: list[CodeChunk] = []
    for start in range(0, len(lines), max_lines):
        end = min(len(lines), start + max_lines)
        text = "\n".join(lines[start:end])
        chunk_symbols = [
            symbol for symbol in symbols if start + 1 <= symbol.line_start <= end
        ]
        chunks.append(
            CodeChunk(
                path=path,
                language=language,
                text=text,
                symbols=chunk_symbols,
                tokens=normalize_tokens(f"{path}\n{text}\n" + " ".join(s.name for s in chunk_symbols)),
            )
        )
    return chunks


def _idf(chunks: list[CodeChunk], query_terms: list[str]) -> dict[str, float]:
    total = max(len(chunks), 1)
    result: dict[str, float] = {}
    for term in set(query_terms):
        docs = sum(1 for chunk in chunks if term in set(chunk.tokens))
        result[term] = math.log((total + 1) / (docs + 1)) + 1.0
    return result


def score_chunk(chunk: CodeChunk, query_terms: list[str], idf: dict[str, float]) -> tuple[float, list[str]]:
    counts = Counter(chunk.tokens)
    score = 0.0
    matched: list[str] = []

    path_tokens = set(normalize_tokens(chunk.path))
    symbol_tokens = {token for symbol in chunk.symbols for token in normalize_tokens(symbol.name)}

    for term in query_terms:
        frequency = counts.get(term, 0)
        if not frequency:
            continue

        weight = idf.get(term, 1.0)
        tf = 1 + math.log(frequency)
        contribution = tf * weight

        if term in path_tokens:
            contribution *= 1.8
        if term in symbol_tokens:
            contribution *= 2.2

        score += contribution
        matched.append(term)

    if chunk.path.lower().endswith(("test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")):
        if any(term in {"test", "regression", "failure"} for term in query_terms):
            score *= 1.25

    return score, sorted(set(matched))


def _snippet(text: str, query_terms: list[str], max_chars: int = 900) -> str:
    lines = text.splitlines()
    if not lines:
        return ""

    lowered = [line.lower() for line in lines]
    best = 0
    best_hits = -1
    for index, line in enumerate(lowered):
        hits = sum(1 for term in query_terms if term in line)
        if hits > best_hits:
            best_hits = hits
            best = index

    start = max(0, best - 8)
    end = min(len(lines), best + 16)
    snippet = "\n".join(lines[start:end]).strip()
    return snippet[:max_chars]


async def search_repository_code(repository_url: str, task: str, limit: int = 8) -> CodeSearchResponse:
    ref = parse_github_repository_url(repository_url)
    client = GitHubClient()

    try:
        repository = await client.repository(ref)
        default_branch = repository.get("default_branch") or "main"
        commit = await client.commit(ref, default_branch)
        tree_sha = commit["commit"]["tree"]["sha"]
        tree = await client.tree(ref, tree_sha)

        candidates = []
        for item in tree.get("tree", []):
            if item.get("type") != "blob" or not item.get("path"):
                continue
            classified = classify_path(item["path"], item.get("size"))
            if classified.ignored or classified.kind != "source":
                continue
            if item.get("size") and item["size"] > 250_000:
                continue
            candidates.append(classified)

        # MVP safety cap. Large-repo pagination/index persistence comes next.
        candidates = candidates[:120]

        chunks: list[CodeChunk] = []
        for file in candidates:
            source = await client.file_content(ref, file.path, default_branch)
            if source is None:
                continue
            chunks.extend(chunk_source(file.path, source, file.language))
    finally:
        await client.close()

    query_terms = normalize_tokens(task)
    idf = _idf(chunks, query_terms)
    ranked = []

    for chunk in chunks:
        score, matched = score_chunk(chunk, query_terms, idf)
        if score <= 0:
            continue
        reasons = [f"Matched task terms: {', '.join(matched[:8])}"]
        if chunk.symbols:
            reasons.append(
                "Relevant symbols: " + ", ".join(symbol.name for symbol in chunk.symbols[:6])
            )
        ranked.append((score, chunk, reasons))

    ranked.sort(key=lambda item: item[0], reverse=True)

    results = [
        CodeEvidence(
            path=chunk.path,
            language=chunk.language,
            score=round(score, 4),
            reasons=reasons,
            symbols=chunk.symbols[:10],
            snippet=_snippet(chunk.text, query_terms),
        )
        for score, chunk, reasons in ranked[:limit]
    ]

    return CodeSearchResponse(
        repository=ref.full_name,
        task=task,
        indexed_files=len(candidates),
        indexed_chunks=len(chunks),
        results=results,
    )
