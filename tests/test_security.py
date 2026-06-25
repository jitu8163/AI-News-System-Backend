from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_token():
    token = create_access_token(subject=42)
    decoded = decode_access_token(token)
    assert decoded == "42"


def test_decode_invalid_token_returns_none():
    assert decode_access_token("not.a.valid.token") is None


def test_decode_tampered_token_returns_none():
    token = create_access_token(subject=1)
    tampered = token[:-5] + "XXXXX"
    assert decode_access_token(tampered) is None
