from app.services.code_intelligence import (
    chunk_source,
    extract_python_symbols,
    normalize_tokens,
    score_chunk,
)


def test_extract_python_symbols() -> None:
    source = """
class AuthService:
    def validate_token(self, token):
        return token

async def refresh_access_token():
    return None
"""
    symbols = extract_python_symbols(source)
    names = {symbol.name for symbol in symbols}
    assert {"AuthService", "validate_token", "refresh_access_token"} <= names


def test_normalize_tokens_expands_identifiers() -> None:
    tokens = normalize_tokens("tokenService")
    assert "token" in tokens
    assert "service" in tokens


def test_chunk_source_carries_symbols() -> None:
    chunks = chunk_source(
        "auth/service.py",
        "def validate_token(token):\n    return token\n",
        "Python",
    )
    assert len(chunks) == 1
    assert chunks[0].symbols[0].name == "validate_token"


def test_symbol_match_boosts_score() -> None:
    chunk = chunk_source(
        "auth/service.py",
        "def validate_token(token):\n    return token\n",
        "Python",
    )[0]
    score, matched = score_chunk(chunk, ["validate", "token"], {"validate": 1.0, "token": 1.0})
    assert score > 0
    assert "token" in matched


def test_query_tokens_expand_engineering_concepts() -> None:
    from app.services.code_intelligence import query_tokens

    tokens = query_tokens("isolated validation before opening a pull request")
    assert "sandbox" in tokens
    assert "validate" in tokens
    assert "pr" in tokens
    assert "create" in tokens


def test_structural_path_match_beats_repeated_prose() -> None:
    from app.services.code_intelligence import CodeChunk, score_chunk

    implementation = CodeChunk(
        path="app/services/sandbox_validation.py",
        language="Python",
        text="def run(): pass",
        symbols=[],
        tokens=["run"],
    )
    prose = CodeChunk(
        path="app/page.tsx",
        language="TypeScript",
        text="validation validation validation validation",
        symbols=[],
        tokens=["validation"] * 4,
    )
    terms = ["sandbox", "validation"]
    idf = {"sandbox": 2.0, "validation": 1.0}

    implementation_score, _ = score_chunk(implementation, terms, idf)
    prose_score, _ = score_chunk(prose, terms, idf)

    assert implementation_score > prose_score
