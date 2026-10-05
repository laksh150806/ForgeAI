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
