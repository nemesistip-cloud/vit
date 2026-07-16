import pytest
from app.services.affiliate_service import AffiliateService

def test_generate_deep_link_betway():
    url = AffiliateService.generate_deep_link("betway", "match123", "sel456")
    assert "betway.com.ng" in url
    assert "ms=match123%2Csel456" in url

def test_generate_deep_link_sportybet():
    url = AffiliateService.generate_deep_link("sportybet", "match123", "sel456")
    assert "sportybet.com" in url
    assert "selectionIds=sel456" in url

def test_generate_multi_selection_sportybet():
    selections = [
        {"match_id": "m1", "selection_id": "s1"},
        {"match_id": "m2", "selection_id": "s2"}
    ]
    url = AffiliateService.generate_multi_selection_link("sportybet", selections)
    assert "selectionIds=s1%2Cs2" in url

def test_generate_multi_selection_betway():
    selections = [
        {"match_id": "m1", "selection_id": "s1"},
        {"match_id": "m2", "selection_id": "s2"}
    ]
    url = AffiliateService.generate_multi_selection_link("betway", selections)
    assert "ms=m1%2Cs1%3Bm2%2Cs2" in url
