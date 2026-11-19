"""AI modullerinin ag gerektirmeyen birim testleri."""

import unittest

from ai_cache import CACHE_TTL_SECONDS, _is_expired, cache_key, get_domain, normalize_url
from ai_prompts import build_batch_prompt, build_categorize_prompt, build_suggest_prompt
from ai_response import FALLBACK_CATEGORY, parse_json_response, validate_result


class ResponseTests(unittest.TestCase):

    def test_parses_fenced_json(self):
        raw = '```json\n{"category_path": ["A"], "confidence": 0.9}\n```'
        self.assertEqual(parse_json_response(raw)["category_path"], ["A"])

    def test_invalid_json_returns_none(self):
        self.assertIsNone(parse_json_response("bu JSON degil"))

    def test_validate_rejects_non_dict(self):
        result = validate_result(["gecersiz"])
        self.assertEqual(result["category_path"], FALLBACK_CATEGORY)
        self.assertEqual(result["confidence"], 0.0)

    def test_validate_clamps_confidence_and_coerces_flags(self):
        result = validate_result({
            "category_path": ["A", "B"],
            "confidence": 3.7,
            "reasoning": 42,
            "is_new_category": "yes",
        })
        self.assertEqual(result["confidence"], 1.0)
        self.assertEqual(result["reasoning"], "42")
        self.assertFalse(result["is_new_category"])

    def test_validate_empty_path_falls_back(self):
        self.assertEqual(validate_result({"category_path": []})["category_path"], FALLBACK_CATEGORY)


class PromptTests(unittest.TestCase):

    def test_categorize_prompt_contains_bookmark(self):
        prompt = build_categorize_prompt("Baslik", "https://ornek.test/x", ["A"])
        self.assertIn("Baslik", prompt)
        self.assertIn("https://ornek.test/x", prompt)
        self.assertIn("category_path", prompt)

    def test_batch_prompt_lists_every_bookmark(self):
        prompt = build_batch_prompt([
            {"title": "Bir", "url": "https://a.test"},
            {"title": "Iki", "url": "https://b.test"},
        ])
        self.assertIn("Bir", prompt)
        self.assertIn("Iki", prompt)

    def test_suggest_prompt_includes_categories(self):
        prompt = build_suggest_prompt([{"title": "X", "url": "https://x.test"}], ["Kategori"])
        self.assertIn("Kategori", prompt)
        self.assertIn("suggested_new_categories", prompt)


class CacheKeyTests(unittest.TestCase):

    def test_domain_strips_www_and_lowercases(self):
        self.assertEqual(get_domain("https://WWW.Example.com/yol"), "example.com")

    def test_domain_of_garbage_is_safe(self):
        self.assertEqual(get_domain(""), "")

    def test_distinct_pages_of_same_domain_keep_distinct_keys(self):
        a = cache_key("https://www.youtube.com/watch?v=aaa111")
        b = cache_key("https://www.youtube.com/watch?v=bbb222")
        self.assertNotEqual(a, b)

    def test_tracking_params_and_fragment_are_stripped(self):
        self.assertEqual(
            normalize_url("https://WWW.Example.com/yol/?utm_source=x&id=7#bolum"),
            "https://example.com/yol/?id=7",
        )

    def test_query_order_does_not_change_key(self):
        self.assertEqual(
            normalize_url("https://ornek.test/x?b=2&a=1"),
            normalize_url("https://ornek.test/x?a=1&b=2"),
        )


class CacheTtlTests(unittest.TestCase):

    def test_fresh_entry_is_valid(self):
        self.assertFalse(_is_expired({"cached_at": 1_000.0}, now=1_000.0 + 10))

    def test_expired_entry_is_detected(self):
        self.assertTrue(_is_expired({"cached_at": 1_000.0}, now=1_000.0 + CACHE_TTL_SECONDS + 1))

    def test_legacy_entry_without_timestamp_is_expired(self):
        self.assertTrue(_is_expired({"category_path": ["A"], "confidence": 0.9}))


class PipelinePathTests(unittest.TestCase):
    """AI'in uydurdugu alt kategoriler gecerli onege indirilmeli."""

    def test_resolves_longest_valid_prefix(self):
        from categories import get_categories
        from ai_pipeline import _resolve_path

        resolved = _resolve_path(
            ["Kültür & Yaşam", "Haber, Blog & Makale", "Uydurma Alt"],
            get_categories(),
        )
        self.assertEqual(resolved, ["Kültür & Yaşam", "Haber, Blog & Makale"])

    def test_unknown_top_level_returns_none(self):
        from categories import get_categories
        from ai_pipeline import _resolve_path

        self.assertIsNone(_resolve_path(["Olmayan Kategori"], get_categories()))

    def test_joined_path_string_is_split(self):
        from categories import get_categories
        from ai_pipeline import _resolve_path

        resolved = _resolve_path(["Kültür & Yaşam > Haber, Blog & Makale"], get_categories())
        self.assertEqual(resolved, ["Kültür & Yaşam", "Haber, Blog & Makale"])


if __name__ == "__main__":
    unittest.main()
