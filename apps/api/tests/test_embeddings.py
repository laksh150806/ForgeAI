from app.services.embeddings import cosine_similarity


def test_cosine_similarity_identical_vectors() -> None:
    assert round(cosine_similarity([1.0, 2.0], [1.0, 2.0]), 6) == 1.0


def test_cosine_similarity_orthogonal_vectors() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
