"""Student identity gate validation (session UX only)."""

from src.identity import (
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


def test_validate_ucm_id_accepts_700_nine_digit():
    assert validate_ucm_id("700782694") is None
    assert validate_ucm_id("700012345") is None
    assert validate_ucm_id("700-782-694") is None


def test_validate_ucm_id_rejects_wrong_shape():
    assert validate_ucm_id("") is not None
    assert validate_ucm_id("123") is not None
    assert validate_ucm_id("abcdefg") is not None
    assert validate_ucm_id("1234567") is not None  # not 700-prefixed / not 9
    assert validate_ucm_id("123456789") is not None  # 9 digits but not 700*
    assert validate_ucm_id("800782694") is not None
    assert validate_ucm_id("70078269") is not None  # 8 digits
    assert validate_ucm_id("7007826940") is not None  # 10 digits
    err = validate_ucm_id("abc")
    assert err is not None
    assert "UCM ID" in err
    assert validate_ucm_id("701782694") is not None  # starts 701, not 700


def test_normalize_and_mask():
    assert normalize_ucm_id("70-001-2345") == "700012345"
    identity = StudentIdentity(full_name="Alex Rivera Santos", ucm_id="700012345")
    assert identity.first_name == "Alex"
    assert identity.masked_id.endswith("2345")
    assert "7000" not in identity.masked_id
