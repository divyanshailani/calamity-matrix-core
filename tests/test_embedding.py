"""Tests for the hardened Hugging Face embedding client (Phase B of the
embedding-bridge incident plan).

Stdlib-only (unittest + mock) so the suite runs without adding a test
dependency. Run with:  python3 -m unittest discover -s tests
"""
import os
import sys
import unittest
from unittest import mock

# Import the module the same way production does (scripts.production.retrieval).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import scripts.production.retrieval as R  # noqa: E402


def make_response(status_code, payload):
    resp = mock.MagicMock()
    resp.status_code = status_code
    if isinstance(payload, Exception):
        resp.json.side_effect = payload
    else:
        resp.json.return_value = payload
    return resp


VALID_VEC = [2.0] * R.VECTOR_DIM  # norm 64 -> each element normalizes to 0.03125


class EmbeddingClientTests(unittest.TestCase):
    def setUp(self):
        R.HF_TOKEN = "test-token"

    def tearDown(self):
        R.HF_TOKEN = ""

    def test_missing_token_fails_fast_without_calling_provider(self):
        R.HF_TOKEN = ""
        with mock.patch.object(R.requests, "post") as post:
            vectors, info = R._hf_embed("the ground shook")
        post.assert_not_called()
        self.assertIsNone(vectors)
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], R.EMBED_MISSING_TOKEN)
        self.assertEqual(info["attempts"], 0)

    def test_permanent_402_is_not_retried(self):
        with mock.patch.object(R.requests, "post", return_value=make_response(402, {})) as post:
            vectors, info = R._hf_embed("the ground shook")
        self.assertIsNone(vectors)
        self.assertEqual(info["reason"], R.EMBED_HTTP)
        self.assertEqual(info["http_status"], 402)
        self.assertEqual(info["attempts"], 1, "a billing rejection must not be retried")
        self.assertEqual(post.call_count, 1)

    def test_permanent_403_is_not_retried(self):
        with mock.patch.object(R.requests, "post", return_value=make_response(403, {})) as post:
            _, info = R._hf_embed("the ground shook")
        self.assertEqual(info["attempts"], 1)
        self.assertEqual(post.call_count, 1)

    def test_transient_then_success_retries_once(self):
        side_effect = [
            make_response(429, {}),
            make_response(200, VALID_VEC),
        ]
        with mock.patch.object(R.requests, "post", side_effect=side_effect) as post:
            vectors, info = R._hf_embed("the ground shook")
        self.assertIsNone(info)
        self.assertEqual(len(vectors), R.VECTOR_DIM)
        self.assertEqual(post.call_count, 2)

    def test_success_vector_is_normalized(self):
        with mock.patch.object(R.requests, "post", return_value=make_response(200, VALID_VEC)):
            vectors, info = R._hf_embed("the ground shook")
        self.assertIsNone(info)
        expected = 2.0 / (64.0)  # sqrt(1024 * 4)
        self.assertAlmostEqual(vectors[0], expected, places=5)
        self.assertAlmostEqual(vectors[-1], expected, places=5)

    def test_wrong_dimension_is_rejected(self):
        with mock.patch.object(R.requests, "post", return_value=make_response(200, [1.0, 2.0, 3.0])):
            vectors, info = R._hf_embed("the ground shook")
        self.assertIsNone(vectors)
        self.assertEqual(info["reason"], R.EMBED_WRONG_DIMENSION)

    def test_nonfinite_vector_is_rejected(self):
        bad = [1.0] * R.VECTOR_DIM
        bad[5] = float("nan")
        with mock.patch.object(R.requests, "post", return_value=make_response(200, bad)):
            vectors, info = R._hf_embed("the ground shook")
        self.assertIsNone(vectors)
        self.assertEqual(info["reason"], R.EMBED_NONFINITE)

    def test_zero_vector_is_rejected(self):
        with mock.patch.object(R.requests, "post", return_value=make_response(200, [0.0] * R.VECTOR_DIM)):
            vectors, info = R._hf_embed("the ground shook")
        self.assertIsNone(vectors)
        self.assertEqual(info["reason"], R.EMBED_ZERO_VECTOR)

    def test_timeout_is_caught_and_counted(self):
        with mock.patch.object(R.requests, "post", side_effect=R.requests.Timeout()) as post:
            vectors, info = R._hf_embed("the ground shook", retries=2)
        self.assertIsNone(vectors)
        self.assertEqual(info["reason"], R.EMBED_TIMEOUT)
        self.assertEqual(info["attempts"], 2)
        self.assertEqual(post.call_count, 2)

    def test_malformed_json_is_marked_not_raised(self):
        with mock.patch.object(R.requests, "post", return_value=make_response(200, ValueError("bad json"))):
            vectors, info = R._hf_embed("the ground shook")
        self.assertIsNone(vectors)
        self.assertEqual(info["reason"], R.EMBED_MALFORMED)


class EmbedWrapperCompatTests(unittest.TestCase):
    """The public wrappers used by the eval harness and reembed script must
    keep returning a plain vector-or-None; only embed_query_meta grew a tuple."""

    def test_embed_query_returns_plain_vector(self):
        R.HF_TOKEN = "test-token"
        with mock.patch.object(R.requests, "post", return_value=make_response(200, VALID_VEC)):
            vectors = R.embed_query("the ground shook")
        self.assertIsInstance(vectors, list)
        self.assertEqual(len(vectors), R.VECTOR_DIM)

    def test_embed_many_returns_list_of_vectors(self):
        R.HF_TOKEN = "test-token"
        payload = [VALID_VEC, VALID_VEC]
        with mock.patch.object(R.requests, "post", return_value=make_response(200, payload)):
            vectors = R.embed_many(["a", "b"])
        self.assertEqual(len(vectors), 2)
        self.assertEqual(len(vectors[0]), R.VECTOR_DIM)


if __name__ == "__main__":
    unittest.main()
