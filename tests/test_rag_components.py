import unittest
from types import SimpleNamespace

from rag.categories import resolve_category
from rag.generator import GroqGenerator
from rag.retriever import retrieve_context


class FakeIndex:
    def search(self, query, limit):
        return [(SimpleNamespace(doc_id="network", index=1), 0.8)]

    def expand(self, chunk, window):
        return "Troubleshooting steps. Resolution steps."


class FakeClient:
    class chat:
        class completions:
            @staticmethod
            def create(**kwargs):
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"category":"Network","resolution":"Restart the adapter."}'))])


class RagComponentTests(unittest.TestCase):
    def test_retriever_expands_context_and_sources(self):
        context = retrieve_context(FakeIndex(), "Wi-Fi", threshold=0.5)
        self.assertEqual(context[1], ["network.md"])
        self.assertIn("Resolution steps", context[0])

    def test_category_fallback(self):
        self.assertEqual(resolve_category("Email"), "software")

    def test_generator_parses_structured_response(self):
        answer = GroqGenerator(client=FakeClient()).generate("Wi-Fi", "Network context")
        self.assertEqual(answer["category"], "network")
        self.assertEqual(answer["resolution"], "Restart the adapter.")


if __name__ == "__main__":
    unittest.main()