"""Tests for the Fireworks provider adapter, provider fallback ordering, vector
space isolation, and the Qwen3 reranker parser.

Stdlib-only (unittest + mock). Run with:  python3 -m unittest discover -s tests
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import scripts.production.retrieval as R  # noqa: E402

VALID = [2.0] * R.VECTOR_DIM


def fw_response(status, payload):
    resp = mock.MagicMock()
    resp.status_code = status
    if isinstance(payload, Exception):
        resp.json.side_effect = payload
    else:
        resp.json.return_value = payload
    return resp


def fw_ok(vectors, tokens=13):
    return fw_response(200, {
        "data": [{"index": i, "embedding": v} for i, v in enumerate(vectors)],
        "usage": {"prompt_tokens": tokens},
        "model": R.FIREWORKS_EMBEDDING_MODEL,
    })


class FireworksEmbedTests(unittest.TestCase):
    def setUp(self):
        self._key = R.FIREWORKS_API_KEY
        R.FIREWORKS_API_KEY = "fw_test"

    def tearDown(self):
        R.FIREWORKS_API_KEY = self._key

    def test_missing_key_fails_without_calling(self):
        R.FIREWORKS_API_KEY = ""
        with mock.patch.object(R.requests, "post") as post:
            vec, info = R._fireworks_embed("quake")
        post.assert_not_called()
        self.assertIsNone(vec)
        self.assertEqual(info["reason"], R.EMBED_MISSING_TOKEN)
        self.assertEqual(info["provider"], "fireworks")

    def test_openai_shape_is_parsed_and_normalized(self):
        with mock.patch.object(R.requests, "post", return_value=fw_ok([VALID])):
            vec, info = R._fireworks_embed("quake")
        self.assertIsNone(info["reason"])
        self.assertEqual(len(vec), R.VECTOR_DIM)
        self.assertAlmostEqual(sum(x * x for x in vec) ** 0.5, 1.0, places=6)

    def test_query_instruction_is_applied_only_to_queries(self):
        with mock.patch.object(R.requests, "post", return_value=fw_ok([VALID])) as post:
            R._fireworks_embed("quake", is_query=True)
        self.assertTrue(post.call_args.kwargs["json"]["input"][0].startswith("Instruct:"))

        with mock.patch.object(R.requests, "post", return_value=fw_ok([VALID])) as post:
            R._fireworks_embed("quake", is_query=False)
        self.assertEqual(post.call_args.kwargs["json"]["input"], ["quake"])

    def test_requested_dimensions_are_sent(self):
        with mock.patch.object(R.requests, "post", return_value=fw_ok([VALID])) as post:
            R._fireworks_embed("quake")
        self.assertEqual(post.call_args.kwargs["json"]["dimensions"], R.FIREWORKS_EMBEDDING_DIMENSIONS)

    def test_out_of_order_indexes_are_reordered_not_trusted(self):
        first = [1.0] * R.VECTOR_DIM
        second = [0.0] * (R.VECTOR_DIM - 1) + [5.0]
        payload = {"data": [{"index": 1, "embedding": second},
                            {"index": 0, "embedding": first}],
                   "usage": {"prompt_tokens": 7}}
        with mock.patch.object(R.requests, "post", return_value=fw_response(200, payload)):
            vecs, info = R._fireworks_embed(["a", "b"])
        self.assertIsNone(info["reason"])
        self.assertAlmostEqual(vecs[0][0], 1.0 / (R.VECTOR_DIM ** 0.5), places=6)
        self.assertAlmostEqual(vecs[1][-1], 1.0, places=6)

    def test_duplicate_index_is_rejected(self):
        payload = {"data": [{"index": 0, "embedding": VALID},
                            {"index": 0, "embedding": VALID}]}
        with mock.patch.object(R.requests, "post", return_value=fw_response(200, payload)):
            vecs, info = R._fireworks_embed(["a", "b"])
        self.assertIsNone(vecs)
        self.assertEqual(info["reason"], R.EMBED_BATCH_MISMATCH)

    def test_short_batch_is_rejected(self):
        with mock.patch.object(R.requests, "post", return_value=fw_ok([VALID])):
            vecs, info = R._fireworks_embed(["a", "b"])
        self.assertIsNone(vecs)
        self.assertEqual(info["reason"], R.EMBED_BATCH_MISMATCH)

    def test_wrong_dimension_is_rejected(self):
        with mock.patch.object(R.requests, "post", return_value=fw_ok([[1.0, 2.0]])):
            vecs, info = R._fireworks_embed("quake")
        self.assertIsNone(vecs)
        self.assertEqual(info["reason"], R.EMBED_WRONG_DIMENSION)

    def test_402_is_not_retried(self):
        with mock.patch.object(R.requests, "post", return_value=fw_response(402, {})) as post:
            vecs, info = R._fireworks_embed("quake")
        self.assertIsNone(vecs)
        self.assertEqual(info["http_status"], 402)
        self.assertEqual(info["attempts"], 1)
        self.assertEqual(post.call_count, 1)

    def test_429_is_retried(self):
        with mock.patch.object(R.requests, "post",
                               side_effect=[fw_response(429, {}), fw_ok([VALID])]) as post:
            vec, info = R._fireworks_embed("quake")
        self.assertIsNone(info["reason"])
        self.assertEqual(post.call_count, 2)

    def test_usage_tokens_are_reported_on_success(self):
        with mock.patch.object(R.requests, "post", return_value=fw_ok([VALID], tokens=99)):
            vec, info = R._fireworks_embed("quake")
        self.assertIsNotNone(vec)
        self.assertEqual(info["prompt_tokens"], 99)


class ProviderFallbackTests(unittest.TestCase):
    def setUp(self):
        self._fw, self._hf = R.FIREWORKS_API_KEY, R.HF_TOKEN
        R.FIREWORKS_API_KEY, R.HF_TOKEN = "fw_test", "hf_test"

    def tearDown(self):
        R.FIREWORKS_API_KEY, R.HF_TOKEN = self._fw, self._hf

    def test_fireworks_success_pins_the_fireworks_column(self):
        with mock.patch.object(R, "_fireworks_embed", return_value=(VALID, {"prompt_tokens": 13, "reason": None})):
            vec, meta = R.embed_query_meta("quake", provider_order=["fireworks", "huggingface"])
        self.assertIsNotNone(vec)
        self.assertEqual(meta["provider"], "fireworks")
        self.assertEqual(meta["column"], "embedding_fireworks")

    def test_fireworks_failure_falls_back_to_hf_and_its_own_column(self):
        fw_fail = (None, {"reason": R.EMBED_HTTP, "http_status": 402, "attempts": 1,
                          "provider": "fireworks"})
        with mock.patch.object(R, "_fireworks_embed", return_value=fw_fail), \
             mock.patch.object(R, "_hf_embed", return_value=(VALID, None)):
            vec, meta = R.embed_query_meta("quake", provider_order=["fireworks", "huggingface"])
        self.assertIsNotNone(vec)
        self.assertEqual(meta["provider"], "huggingface")
        self.assertEqual(meta["column"], R.PROVIDERS["huggingface"]["column"])
        self.assertEqual(meta["failures"][0]["http_status"], 402)

    def test_both_providers_down_returns_no_column(self):
        fail = (None, {"reason": R.EMBED_HTTP, "http_status": 402, "attempts": 1})
        with mock.patch.object(R, "_fireworks_embed", return_value=fail), \
             mock.patch.object(R, "_hf_embed", return_value=fail):
            vec, meta = R.embed_query_meta("quake", provider_order=["fireworks", "huggingface"])
        self.assertIsNone(vec)
        self.assertIsNone(meta["column"])
        self.assertEqual(len(meta["failures"]), 2)

    def test_provider_columns_are_never_shared(self):
        self.assertNotEqual(R.PROVIDERS["fireworks"]["column"],
                            R.PROVIDERS["huggingface"]["column"])

    def test_embed_col_rejects_unknown_column(self):
        with self.assertRaises(ValueError):
            R._embed_col("embedding_evil; DROP TABLE")
        self.assertEqual(R._embed_col("embedding_fireworks"), "embedding_fireworks")


class RerankTests(unittest.TestCase):
    def setUp(self):
        self._key = R.FIREWORKS_API_KEY
        R.FIREWORKS_API_KEY = "fw_test"

    def tearDown(self):
        R.FIREWORKS_API_KEY = self._key

    def test_scores_are_sorted_descending_by_relevance(self):
        payload = {"data": [{"index": 0, "relevance_score": 0.01},
                            {"index": 1, "relevance_score": 0.90},
                            {"index": 2, "relevance_score": 0.44}],
                   "usage": {"prompt_tokens": 171}}
        with mock.patch.object(R.requests, "post", return_value=fw_response(200, payload)):
            order, meta = R.rerank("q", ["a", "b", "c"])
        self.assertEqual(order, [1, 2, 0])
        self.assertEqual(meta["prompt_tokens"], 171)

    def test_documents_are_truncated_to_budget(self):
        long_doc = "x" * (R.RERANK_DOC_CHARS + 500)
        payload = {"data": [{"index": 0, "relevance_score": 0.5}]}
        with mock.patch.object(R.requests, "post", return_value=fw_response(200, payload)) as post:
            R.rerank("q", [long_doc])
        self.assertEqual(len(post.call_args.kwargs["json"]["documents"][0]), R.RERANK_DOC_CHARS)

    def test_failure_returns_none_so_caller_keeps_rrf_order(self):
        with mock.patch.object(R.requests, "post", return_value=fw_response(500, {})):
            order, meta = R.rerank("q", ["a"], retries=1)
        self.assertIsNone(order)
        self.assertEqual(meta["http_status"], 500)

    def test_bad_index_is_rejected(self):
        payload = {"data": [{"index": 9, "relevance_score": 0.5}]}
        with mock.patch.object(R.requests, "post", return_value=fw_response(200, payload)):
            order, meta = R.rerank("q", ["a"])
        self.assertIsNone(order)
        self.assertEqual(meta["reason"], R.EMBED_BATCH_MISMATCH)

    def test_empty_documents_short_circuits(self):
        with mock.patch.object(R.requests, "post") as post:
            order, _ = R.rerank("q", [])
        post.assert_not_called()
        self.assertEqual(order, [])


if __name__ == "__main__":
    unittest.main()
