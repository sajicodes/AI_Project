"""Student identity gate validation (session UX only)."""

from src.ui.identity import (
    StudentIdentity,
    normalize_ucm_id,
    validate_full_name,
    validate_ucm_id,
)


def test_validate_full_name():
    assert validate_full_name("") is not None
    assert validate_full_name("A") is not None
    assert validate_full_name("12345") is not None
    assert validate_full_name("Alex Rivera") is None
    assert validate_full_name("  Sam  Lee  ") is None


def test_validate_ucm_id():
    assert validate_ucm_id("") is not None
    assert validate_ucm_id("123") is not None
    assert validate_ucm_id("abcdefg") is not None
    assert validate_ucm_id("1234567") is None
    assert validate_ucm_id("12-345-678") is None  # 8 digits after normalize
    assert validate_ucm_id("700012345") is None
    assert validate_ucm_id("1234567890") is not None  # 10 digits too long


def test_normalize_and_mask():
    assert normalize_ucm_id("70-001-2345") == "700012345"
    identity = StudentIdentity(full_name="Alex Rivera Santos", ucm_id="700012345")
    assert identity.first_name == "Alex"
    assert identity.masked_id.endswith("2345")
    assert "7000" not in identity.masked_id
