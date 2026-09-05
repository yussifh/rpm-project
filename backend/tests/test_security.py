"""
Unit tests for app.core.security — pure logic, no database required.
Deliberately kept separate from the integration tests (test_auth.py),
which exercise the full HTTP flow; these test the primitives in isolation
so a failure here points directly at hashing/token logic, not routing or
DB wiring.
"""

import pytest
from jose import JWTError

from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("SecurePass123")
        assert hashed != "SecurePass123"

    def test_verify_correct_password(self):
        hashed = hash_password("SecurePass123")
        assert verify_password("SecurePass123", hashed) is True

    def test_verify_incorrect_password(self):
        hashed = hash_password("SecurePass123")
        assert verify_password("WrongPassword", hashed) is False

    def test_same_password_hashed_twice_produces_different_hashes(self):
        # bcrypt salts automatically — two hashes of the same password must differ.
        first = hash_password("SecurePass123")
        second = hash_password("SecurePass123")
        assert first != second
        # ...but both still verify correctly against the original password.
        assert verify_password("SecurePass123", first)
        assert verify_password("SecurePass123", second)


class TestTokenLifecycle:
    def test_access_token_round_trip(self):
        token = create_access_token(user_id="user-123", role="patient")
        payload = decode_token(token)

        assert payload["sub"] == "user-123"
        assert payload["role"] == "patient"
        assert payload["type"] == TokenType.ACCESS.value

    def test_refresh_token_round_trip_and_has_jti(self):
        token, jti, expires_in = create_refresh_token(user_id="user-456", role="admin")
        payload = decode_token(token)

        assert payload["sub"] == "user-456"
        assert payload["type"] == TokenType.REFRESH.value
        assert payload["jti"] == jti
        assert expires_in > 0

    def test_two_refresh_tokens_have_different_jti(self):
        _, jti_one, _ = create_refresh_token(user_id="user-789", role="patient")
        _, jti_two, _ = create_refresh_token(user_id="user-789", role="patient")
        assert jti_one != jti_two

    def test_tampered_token_fails_to_decode(self):
        token = create_access_token(user_id="user-123", role="patient")
        tampered = token[:-4] + "abcd"
        with pytest.raises(JWTError):
            decode_token(tampered)

    def test_garbage_token_fails_to_decode(self):
        with pytest.raises(JWTError):
            decode_token("not.a.real.jwt.token")
