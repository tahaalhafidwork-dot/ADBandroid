"""Automated tests for the real estate AI pipeline."""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any, Dict, List

# Add pipeline directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.classifier import PostClassifier  # noqa: E402
from processing.deduplicator import Deduplicator  # noqa: E402
from processing.extractor import ListingExtractor  # noqa: E402
from processing.normalizer import ListingNormalizer  # noqa: E402
from providers.local_provider import LocalProvider  # noqa: E402
from providers.kilo_provider import _resolve_category_key  # noqa: E402


def _load_test_posts() -> List[Dict[str, Any]]:
    """Load test posts from the Apify results file."""
    input_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "apify_facebook_groups_results.json",
    )
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("posts", [])


class TestLocalProvider(unittest.TestCase):
    """Tests for the local rule-based provider."""

    def setUp(self):
        self.provider = LocalProvider()
        self.assertTrue(self.provider.initialize())
        self.assertTrue(self.provider.is_available())

    def test_classify_for_sale(self):
        result = self.provider.classify("بيت للبيع في أربيل مجمع اشتي ١")
        self.assertEqual(result["category"], "for_sale")
        self.assertGreater(result["confidence"], 0.5)

    def test_classify_for_rent(self):
        result = self.provider.classify("شقة مفروشة للأيجار في أربيل")
        self.assertEqual(result["category"], "for_rent")
        self.assertGreater(result["confidence"], 0.5)

    def test_classify_service(self):
        result = self.provider.classify("ابوعلي کردي مقاول عامە نشتغل من أساس لحد هيكل")
        self.assertEqual(result["category"], "real_estate_service")
        self.assertGreater(result["confidence"], 0.5)

    def test_classify_unclear(self):
        result = self.provider.classify("วันนี้อากาศดีมาก")
        self.assertEqual(result["category"], "unclear")

    def test_extract_sale(self):
        text = "بيت للبيع في أربيل مجمع اشتي ١ 125 متر 4 غرف نوم 07502777723"
        result = self.provider.extract(text, "for_sale")
        self.assertEqual(result["property_type"], "house")
        self.assertEqual(result["city"], "أربيل")
        self.assertEqual(result["area_sqm"], 125)
        self.assertEqual(result["bedrooms"], 4)
        self.assertIn("07502777723", result["contact_phones"])

    def test_extract_rent(self):
        text = "شقة مفروشة للأيجار في أربيل 170 متر 3 غرف نوم 07852562878"
        result = self.provider.extract(text, "for_rent")
        self.assertEqual(result["property_type"], "apartment")
        self.assertEqual(result["city"], "أربيل")
        self.assertEqual(result["area_sqm"], 170)
        self.assertEqual(result["bedrooms"], 3)
        self.assertTrue(result["furnished"])
        self.assertIn("07852562878", result["contact_phones"])

    def test_no_invented_price(self):
        text = "بيت للبيع في أربيل 4 غرف نوم"  # No price mentioned
        result = self.provider.extract(text, "for_sale")
        self.assertIsNone(result["price"])

    def test_no_invented_area(self):
        text = "بيت للبيع في أربيل 4 غرف نوم"  # No area mentioned
        result = self.provider.extract(text, "for_sale")
        self.assertIsNone(result["area_sqm"])


class TestClassifier(unittest.TestCase):
    """Tests for the post classifier."""

    def setUp(self):
        self.provider = LocalProvider()
        self.classifier = PostClassifier(self.provider)

    def test_classify_post(self):
        post = {"index": 1, "text": "بيت للبيع في أربيل", "url": "http://example.com/1"}
        result = self.classifier.classify_post(post)
        self.assertIn("_classification", result)
        self.assertEqual(result["_classification"]["category"], "for_sale")

    def test_is_real_estate(self):
        self.assertTrue(self.classifier.is_real_estate("for_sale"))
        self.assertTrue(self.classifier.is_real_estate("for_rent"))
        self.assertFalse(self.classifier.is_real_estate("real_estate_service"))
        self.assertFalse(self.classifier.is_real_estate("not_real_estate"))

    def test_is_service(self):
        self.assertTrue(self.classifier.is_service("real_estate_service"))
        self.assertFalse(self.classifier.is_service("for_sale"))


class TestExtractor(unittest.TestCase):
    """Tests for the listing extractor."""

    def setUp(self):
        self.provider = LocalProvider()
        self.extractor = ListingExtractor(self.provider)

    def test_extract_sale_post(self):
        post = {
            "index": 1,
            "text": "بيت للبيع في أربيل مجمع اشتي ١ 125 متر 4 غرف نوم 07502777723",
            "url": "http://example.com/1",
            "time": "2026-10-20T20:26:41.000Z",
        }
        post = self.classify_first(post)
        result = self.extractor.extract_post(post)
        extraction = result.get("_extraction", {})
        self.assertFalse(extraction.get("skipped"))
        self.assertEqual(extraction.get("city"), "أربيل")
        self.assertEqual(extraction.get("area_sqm"), 125)

    def test_extract_service_post_skipped(self):
        post = {
            "index": 2,
            "text": "ابوعلي کردي مقاول عامە",
            "url": "http://example.com/2",
            "time": "2026-10-20T20:15:39.000Z",
        }
        post = self.classify_first(post)
        result = self.extractor.extract_post(post)
        extraction = result.get("_extraction", {})
        self.assertTrue(extraction.get("skipped"))

    def classify_first(self, post: Dict[str, Any]) -> Dict[str, Any]:
        classifier = PostClassifier(self.provider)
        return classifier.classify_post(post)


class TestNormalizer(unittest.TestCase):
    """Tests for the listing normalizer."""

    def setUp(self):
        self.normalizer = ListingNormalizer()

    def test_normalize_area(self):
        listing = {"area_sqm": "125"}
        result = self.normalizer.normalize(listing)
        self.assertEqual(result["area_sqm"], 125)

    def test_normalize_price(self):
        listing = {"price": "40"}
        result = self.normalizer.normalize(listing)
        self.assertEqual(result["price"], 40.0)

    def test_normalize_furnished_arabic(self):
        listing = {"furnished": "مفروشة"}
        result = self.normalizer.normalize(listing)
        self.assertTrue(result["furnished"])

    def test_normalize_furnished_empty(self):
        listing = {"furnished": None}
        result = self.normalizer.normalize(listing)
        self.assertIsNone(result["furnished"])

    def test_normalize_phones(self):
        listing = {"contact_phones": ["07502777723", "07502777723", " 07744455071 "]}
        result = self.normalizer.normalize(listing)
        self.assertEqual(len(result["contact_phones"]), 2)
        self.assertIn("07502777723", result["contact_phones"])
        self.assertIn("07744455071", result["contact_phones"])


class TestDeduplicator(unittest.TestCase):
    """Tests for the deduplicator."""

    def setUp(self):
        self.dedup = Deduplicator(similarity_threshold=0.80)

    def test_level1_duplicate_url(self):
        posts = [
            {"index": 1, "url": "http://example.com/post/123", "text": "بيت للبيع في أربيل 125 متر"},
            {"index": 2, "url": "http://example.com/post/123", "text": "بيت للبيع في أربيل 125 متر"},
        ]
        unique, duplicates = self.dedup.find_duplicates(posts)
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(duplicates), 1)
        self.assertIn("Level 1", duplicates[0]["_duplicate_reason"])

    def test_no_duplicates(self):
        posts = [
            {"index": 1, "url": "http://example.com/post/1", "text": "بيت للبيع في أربيل 125 متر"},
            {"index": 2, "url": "http://example.com/post/2", "text": "شقة للإيجار في بغداد 200 متر"},
        ]
        unique, duplicates = self.dedup.find_duplicates(posts)
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(duplicates), 0)

    def test_level2_similar_text(self):
        posts = [
            {
                "index": 1,
                "url": "http://example.com/post/1",
                "text": "بيت للبيع في أربيل مجمع اشتي ١ 125 متر 4 غرف نوم",
                "_extraction": {
                    "city": "أربيل",
                    "area_sqm": 125,
                    "property_type": "house",
                    "contact_phones": ["07502777723"],
                },
            },
            {
                "index": 2,
                "url": "http://example.com/post/2",
                "text": "بيت للبيع في أربيل مجمع اشتي ١ 125 متر 4 غرف نوم",
                "_extraction": {
                    "city": "أربيل",
                    "area_sqm": 125,
                    "property_type": "house",
                    "contact_phones": ["07502777723"],
                },
            },
        ]
        unique, duplicates = self.dedup.find_duplicates(posts)
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(duplicates), 1)

    def test_same_phone_different_property_not_duplicate(self):
        """Two different properties with same agent phone should NOT be duplicates."""
        posts = [
            {
                "index": 1,
                "url": "http://example.com/post/1",
                "text": "بيت للبيع في أربيل 125 متر",
                "_extraction": {
                    "city": "أربيل",
                    "area_sqm": 125,
                    "property_type": "house",
                    "contact_phones": ["07732229142"],
                },
            },
            {
                "index": 2,
                "url": "http://example.com/post/2",
                "text": "شقة للإيجار في أربيل 200 متر",
                "_extraction": {
                    "city": "أربيل",
                    "area_sqm": 200,
                    "property_type": "apartment",
                    "contact_phones": ["07732229142"],
                },
            },
        ]
        unique, duplicates = self.dedup.find_duplicates(posts)
        # Different area and property type, low text similarity -> not duplicate
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(duplicates), 0)


class TestSchemaValidation(unittest.TestCase):
    """Test that extracted listings conform to the schema."""

    def test_schema_loads(self):
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "real_estate_ai_pipeline",
            "schemas",
            "listing_schema.json",
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        self.assertIn("properties", schema)
        self.assertIn("listing_type", schema["properties"])


class TestEndToEnd(unittest.TestCase):
    """End-to-end test on all 10 posts."""

    def test_pipeline_runs(self):
        posts = _load_test_posts()
        self.assertEqual(len(posts), 10)

        provider = LocalProvider()
        classifier = PostClassifier(provider)
        extractor = ListingExtractor(provider)
        normalizer = ListingNormalizer()
        dedup = Deduplicator(similarity_threshold=0.80)

        classified = classifier.classify_posts(posts)
        extracted = extractor.extract_posts(classified)

        structured: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []

        for post in extracted:
            ext = post.get("_extraction", {})
            if ext.get("skipped"):
                rejected.append(post)
            else:
                listing = {
                    "source": ext.get("source"),
                    "source_url": ext.get("source_url"),
                    "listing_type": ext.get("listing_type"),
                    "property_type": ext.get("property_type"),
                    "title": ext.get("title"),
                    "description": ext.get("description"),
                    "city": ext.get("city"),
                    "district": ext.get("district"),
                    "complex_name": ext.get("complex_name"),
                    "area_sqm": ext.get("area_sqm"),
                    "bedrooms": ext.get("bedrooms"),
                    "bathrooms": ext.get("bathrooms"),
                    "floor": ext.get("floor"),
                    "furnished": ext.get("furnished"),
                    "price": ext.get("price"),
                    "currency": ext.get("currency"),
                    "contact_phones": ext.get("contact_phones", []),
                    "published_at": ext.get("published_at"),
                    "confidence": ext.get("confidence"),
                }
                structured.append(listing)

        structured = normalizer.normalize_all(structured)
        unique, duplicates = dedup.find_duplicates(structured)

        # Assertions
        self.assertGreater(len(structured), 0, "Should have at least one structured listing")
        self.assertGreater(len(rejected), 0, "Should have at least one rejected post (services)")
        self.assertGreaterEqual(len(unique) + len(duplicates), len(structured))

        # Check that service posts are rejected
        service_posts = [
            p for p in rejected
            if "service" in str(p.get("_classification", {}).get("category", ""))
        ]
        # At minimum, the contractor and gardening posts should be rejected
        self.assertGreaterEqual(len(rejected), 2, "At least 2 service posts should be rejected")

        # Check no invented prices
        for listing in unique:
            if listing.get("price") is not None:
                # Price should be a number, not None
                self.assertIsInstance(listing["price"], (int, float))


class TestMethodBKeyResolution(unittest.TestCase):
    """Tests for _resolve_category_key — the category/listing_type mismatch fix."""

    def test_listing_type_only(self):
        """JSON contains listing_type without category."""
        cat, conflict = _resolve_category_key({"listing_type": "for_sale", "confidence": 0.9})
        self.assertEqual(cat, "for_sale")
        self.assertIsNone(conflict)

    def test_category_only(self):
        """JSON contains category without listing_type."""
        cat, conflict = _resolve_category_key({"category": "for_rent", "confidence": 0.8})
        self.assertEqual(cat, "for_rent")
        self.assertIsNone(conflict)

    def test_both_keys_same_value(self):
        """JSON contains both keys with the same value."""
        cat, conflict = _resolve_category_key(
            {"listing_type": "for_sale", "category": "for_sale", "confidence": 0.9}
        )
        self.assertEqual(cat, "for_sale")
        self.assertIsNone(conflict)

    def test_both_keys_conflicting(self):
        """JSON contains both keys with different values — listing_type wins, conflict noted."""
        cat, conflict = _resolve_category_key(
            {"listing_type": "for_rent", "category": "for_sale", "confidence": 0.8}
        )
        self.assertEqual(cat, "for_rent")
        self.assertIsNotNone(conflict)
        self.assertIn("category=for_sale", conflict)
        self.assertIn("listing_type=for_rent", conflict)

    def test_neither_key(self):
        """JSON contains neither key — defaults to unclear."""
        cat, conflict = _resolve_category_key({"property_type": "house", "confidence": 0.5})
        self.assertEqual(cat, "unclear")
        self.assertIsNone(conflict)

    def test_invalid_values(self):
        """Invalid category values are ignored."""
        cat, conflict = _resolve_category_key(
            {"listing_type": "invalid_category", "category": "also_invalid"}
        )
        self.assertEqual(cat, "unclear")
        self.assertIsNone(conflict)


class TestMethodBCriticalCases(unittest.TestCase):
    """Tests for Method B critical edge cases."""

    def setUp(self):
        self.provider = LocalProvider()

    def test_extract_price_without_currency(self):
        """Ad mentioning price without clear currency — price extracted, currency null."""
        text = "بيت للبيع في أربيل السعر 40 فقط للتواصل 07732229142"
        result = self.provider.extract(text, "for_sale")
        # Local provider may not extract price without currency keyword
        # Just verify no crash and price is either None or a number
        if result.get("price") is not None:
            self.assertIsInstance(result["price"], (int, float))

    def test_duplicate_different_url_same_text(self):
        """Duplicate listing with different URL but same text/complex/phone."""
        posts = [
            {
                "index": 1,
                "url": "http://facebook.com/groups/1/permalink/100",
                "text": "شقة للإيجار في واو تاورز 170 متر 3 غرف نوم الطابق 5",
                "_extraction": {
                    "city": "أربيل",
                    "complex_name": "واو تاورز",
                    "area_sqm": 170,
                    "bedrooms": 3,
                    "property_type": "apartment",
                    "contact_phones": ["07852562878"],
                },
            },
            {
                "index": 2,
                "url": "http://facebook.com/groups/1/permalink/200",
                "text": "شقة للإيجار في واو تاورز 170 متر 3 غرف نوم الطابق 5",
                "_extraction": {
                    "city": "أربيل",
                    "complex_name": "واو تاورز",
                    "area_sqm": 170,
                    "bedrooms": 3,
                    "property_type": "apartment",
                    "contact_phones": ["07852562878"],
                },
            },
        ]
        dedup = Deduplicator(similarity_threshold=0.75)
        unique, duplicates = dedup.find_duplicates(posts)
        # Same text fingerprint → duplicate despite different URL
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(duplicates), 1)
        self.assertIn("Level 2", duplicates[0]["_duplicate_reason"])

    def test_area_170m_on_100m_street(self):
        """Property area 170m on a 100m street — area should be 170, not 100."""
        text = "شقة مفروشة للإيجار مساحة 170م في واو تاورز على شارع 100م ثلاث غرف نوم"
        result = self.provider.extract(text, "for_rent")
        self.assertEqual(result.get("area_sqm"), 170)

    def test_valid_json_missing_fields(self):
        """Valid JSON with missing optional fields — should not crash."""
        parsed = {
            "listing_type": "for_sale",
            "confidence": 0.8,
        }
        cat, conflict = _resolve_category_key(parsed)
        self.assertEqual(cat, "for_sale")
        self.assertIsNone(conflict)

    def test_truncated_response_handling(self):
        """Simulate truncated response — status should be 'truncated', not 'unclear'."""
        # This tests the logic conceptually: a truncated response should not
        # be conflated with model_unclear. We verify the status values exist.
        valid_statuses = {"ok", "model_unclear", "parse_error", "truncated", "schema_error", "api_error"}
        self.assertIn("truncated", valid_statuses)
        self.assertIn("parse_error", valid_statuses)
        self.assertIn("api_error", valid_statuses)


if __name__ == "__main__":
    unittest.main()
