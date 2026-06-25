from app.utils.hashing import compute_content_hash, normalize_text


def test_normalize_text_strips_and_lowercases():
    assert normalize_text("  Hello  World  ") == "hello world"


def test_normalize_text_collapses_whitespace():
    assert normalize_text("a   b\tc") == "a b c"


def test_compute_content_hash_is_deterministic():
    h1 = compute_content_hash("Dengue outbreak", "https://example.com/article")
    h2 = compute_content_hash("Dengue outbreak", "https://example.com/article")
    assert h1 == h2


def test_compute_content_hash_is_64_chars():
    h = compute_content_hash("title", "https://url.com")
    assert len(h) == 64


def test_compute_content_hash_differs_for_different_inputs():
    h1 = compute_content_hash("Title A", "https://url.com")
    h2 = compute_content_hash("Title B", "https://url.com")
    assert h1 != h2


def test_compute_content_hash_normalizes_before_hashing():
    h1 = compute_content_hash("  Dengue  ", "https://example.com/")
    h2 = compute_content_hash("dengue", "https://example.com/")
    assert h1 == h2
