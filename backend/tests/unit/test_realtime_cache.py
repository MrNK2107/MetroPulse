"""Tests for cache TTL eviction in app/realtime.py.

Tests the in-memory TTL cache: _cache_key, _cache_get, _cache_set,
_evict_expired, MAX_CACHE_SIZE, and DEFAULT_CACHE_TTL.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from app.realtime import (
    DEFAULT_CACHE_TTL,
    MAX_CACHE_SIZE,
    _cache_get,
    _cache_key,
    _cache_set,
    _evict_expired,
    _response_cache,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the response cache before and after each test."""
    _response_cache.clear()
    yield
    _response_cache.clear()


# ── Test: cache key generation ─────────────────────────────────────────


def test_cache_key_deterministic():
    """Same URL + params should produce the same key."""
    k1 = _cache_key("http://example.com", {"q": "test"})
    k2 = _cache_key("http://example.com", {"q": "test"})
    assert k1 == k2


def test_cache_key_different_urls():
    """Different URLs should produce different keys."""
    k1 = _cache_key("http://example.com/a", None)
    k2 = _cache_key("http://example.com/b", None)
    assert k1 != k2


def test_cache_key_different_params():
    """Different params should produce different keys."""
    k1 = _cache_key("http://example.com", {"q": "a"})
    k2 = _cache_key("http://example.com", {"q": "b"})
    assert k1 != k2


def test_cache_key_none_params():
    """None params should work."""
    k = _cache_key("http://example.com", None)
    assert isinstance(k, str)
    assert len(k) == 32  # MD5 hex digest length


# ── Test: cache set and get ────────────────────────────────────────────


def test_cache_set_and_get():
    """Setting a value should be retrievable via _cache_get."""
    _cache_set("http://example.com", {"q": "test"}, "response_data")
    result = _cache_get("http://example.com", {"q": "test"})
    assert result == "response_data"


def test_cache_get_miss():
    """Getting a key that doesn't exist should return None."""
    result = _cache_get("http://nonexistent.com", None)
    assert result is None


def test_cache_overwrite():
    """Setting the same key twice should overwrite the value."""
    _cache_set("http://example.com", None, "first")
    _cache_set("http://example.com", None, "second")
    result = _cache_get("http://example.com", None)
    assert result == "second"


# ── Test: cache TTL expiration ─────────────────────────────────────────


def test_cache_ttl_expiration():
    """Entries should expire after their TTL."""
    _cache_set("http://example.com", None, "data", ttl=1)

    # Should be available immediately
    assert _cache_get("http://example.com", None) == "data"

    # Advance time past TTL
    with patch("app.realtime.time") as mock_time:
        mock_time.time.return_value = time.time() + 2
        mock_time.time.side_effect = None
        # _cache_get checks time.time() < entry[0]
        result = _cache_get("http://example.com", None)
        assert result is None


def test_cache_ttl_within_window():
    """Entries should be available within their TTL window."""
    _cache_set("http://example.com", None, "data", ttl=300)

    with patch("app.realtime.time") as mock_time:
        mock_time.time.return_value = time.time() + 100  # 100s < 300s TTL
        mock_time.time.side_effect = None
        result = _cache_get("http://example.com", None)
        assert result == "data"


def test_default_ttl_is_five_minutes():
    """Default TTL should be 300 seconds (5 minutes)."""
    assert DEFAULT_CACHE_TTL == 300


# ── Test: _evict_expired() removes old entries ─────────────────────────


def test_evict_expired_removes_old_entries():
    """_evict_expired should remove entries whose TTL has elapsed."""
    _cache_set("http://old.com", None, "old_data", ttl=1)
    _cache_set("http://new.com", None, "new_data", ttl=300)

    # Advance time past the old entry's TTL
    with patch("app.realtime.time") as mock_time:
        mock_time.time.return_value = time.time() + 2
        mock_time.time.side_effect = None
        _evict_expired()

    # Old entry should be gone, new entry should remain
    assert "http://old.com" not in str(_response_cache.keys()) or \
           _cache_get("http://old.com", None) is None
    # Note: _cache_get also checks TTL, so we verify via _response_cache directly
    assert len(_response_cache) == 1


def test_evict_expired_keeps_valid_entries():
    """_evict_expired should not remove entries that haven't expired."""
    _cache_set("http://valid.com", None, "data", ttl=300)
    _evict_expired()
    assert len(_response_cache) == 1


def test_evict_expired_on_empty_cache():
    """_evict_expired should be a no-op on empty cache."""
    _evict_expired()
    assert len(_response_cache) == 0


def test_evict_expired_removes_all_expired():
    """Multiple expired entries should all be removed."""
    _cache_set("http://a.com", None, "a", ttl=1)
    _cache_set("http://b.com", None, "b", ttl=1)
    _cache_set("http://c.com", None, "c", ttl=300)

    with patch("app.realtime.time") as mock_time:
        mock_time.time.return_value = time.time() + 2
        mock_time.time.side_effect = None
        _evict_expired()

    assert len(_response_cache) == 1  # only "c" survives


# ── Test: cache max size eviction ──────────────────────────────────────


def test_max_cache_size_is_512():
    """MAX_CACHE_SIZE should be 512."""
    assert MAX_CACHE_SIZE == 512


def test_cache_evicts_oldest_when_full():
    """When cache is at capacity, oldest entries should be evicted."""
    # Fill cache to max
    for i in range(MAX_CACHE_SIZE):
        _cache_set(f"http://example.com/{i}", None, f"data_{i}", ttl=300)

    assert len(_response_cache) == MAX_CACHE_SIZE

    # Add one more — should trigger eviction of ~25% oldest
    _cache_set("http://new.com", None, "new_data", ttl=300)

    # Cache should be smaller than max + 1
    assert len(_response_cache) <= MAX_CACHE_SIZE
    # The new entry should be present
    assert _cache_get("http://new.com", None) == "new_data"


def test_cache_eviction_preserves_newer_entries():
    """Eviction should keep newer entries and drop older ones."""
    # Fill to capacity with short TTL
    for i in range(MAX_CACHE_SIZE):
        _cache_set(f"http://old.com/{i}", None, f"old_{i}", ttl=300)

    # Add a new entry
    _cache_set("http://brand_new.com", None, "brand_new", ttl=600)

    # brand_new should survive since its expiry is later
    found = False
    for key, (exp, val) in _response_cache.items():
        if val == "brand_new":
            found = True
            break
    assert found


# ── Test: _cache_set triggers eviction ─────────────────────────────────


def test_cache_set_calls_evict_expired():
    """_cache_set should call _evict_expired before inserting."""
    with patch("app.realtime._evict_expired") as mock_evict:
        _cache_set("http://example.com", None, "data")
        mock_evict.assert_called_once()
