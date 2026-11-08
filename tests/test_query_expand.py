"""Query expansion and level inference helpers."""

from src.query_expand import expand_query, infer_level_hint, lexical_terms


def test_expand_thesis_query():
    variants = expand_query("What's the difference between thesis and non-thesis master's?")
    assert variants[0].startswith("What's the difference")
    joined = " ".join(variants).lower()
    assert "thesis option" in joined or "non-thesis" in joined
    assert len(variants) >= 2


def test_expand_probation_query():
    variants = expand_query("academic probation GPA requirements")
    assert any("probation" in v.lower() for v in variants)
    assert len(variants) >= 2


def test_infer_level_hint():
    assert infer_level_hint("thesis vs non-thesis master's") == "graduate"
    assert infer_level_hint("undergraduate academic probation") == "undergraduate"
    assert infer_level_hint("what is the refund policy?") is None


def test_lexical_terms_include_non_thesis():
    terms = lexical_terms("thesis vs non-thesis master's options")
    assert "non-thesis" in terms or "thesis" in terms
