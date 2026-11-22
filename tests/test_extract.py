"""Confiro paginação e autores truncados com respostas pequenas simuladas."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import Config
from src.extract import collect


def work(identifier: str, authors: int = 1) -> dict:
    return {"id": f"https://openalex.org/{identifier}",
            "authorships": [{"institutions": [{"id": "https://openalex.org/I1",
                                               "country_code": "BR"}]}] * authors}


class ExtractTests(unittest.TestCase):
    @patch.dict("os.environ", {"OPENALEX_API_KEY": "chave-ficticia"})
    @patch("src.extract.HttpClient")
    def test_cursor_paging_and_manifest_do_not_store_key(self, client_class) -> None:
        client = client_class.return_value
        client.get.side_effect = [
            {"results": [work("W1"), work("W2")], "meta": {"count": 3, "next_cursor": "pagina-2"}},
            {"results": [work("W3")], "meta": {"count": 3, "next_cursor": None}},
            {"results": [{"id": "https://openalex.org/I1"}]},
            [{"id": 1}],
        ]
        with tempfile.TemporaryDirectory() as directory:
            manifest = collect(Config(2023, 2023, 2, 2, 0), Path(directory))
            self.assertTrue(manifest["complete"])
            self.assertEqual(manifest["coverage"][0]["fetched"], 3)
            self.assertEqual(client.get.call_args_list[1].args[1]["cursor"], "pagina-2")
            for path in Path(directory).glob("*.json"):
                self.assertNotIn("chave-ficticia", path.read_text())

    @patch("src.extract.HttpClient")
    def test_expands_authorships_before_collecting_institutions(self, client_class) -> None:
        client = client_class.return_value
        full = {"authorships": [{"institutions": [{"id": "https://openalex.org/I2",
                                                  "country_code": "BR"}]}]}
        client.get.side_effect = [
            {"results": [work("W1", 100)], "meta": {"count": 1, "next_cursor": None}},
            full, {"results": [{"id": "https://openalex.org/I2"}]}, [{"id": 1}],
        ]
        with tempfile.TemporaryDirectory() as directory:
            manifest = collect(Config(2023, 2023, 1, 1, 0), Path(directory))
            self.assertEqual(manifest["expanded_authorships"], 1)
            stored = json.loads((Path(directory) / "works.json").read_text())
            self.assertEqual(stored[0]["authorships"], full["authorships"])
            self.assertEqual(client.get.call_args_list[2].args[1]["filter"], "openalex_id:I2")

    @patch.dict("os.environ", {}, clear=True)
    def test_more_pages_require_key(self) -> None:
        with self.assertRaises(ValueError):
            Config(2023, 2023, 2).validate()

    def test_current_year_and_oversized_page_are_rejected(self) -> None:
        for config in [Config(2023, 9999), Config(2023, 2024, 1, 101)]:
            with self.assertRaises(ValueError):
                config.validate()


if __name__ == "__main__":
    unittest.main()
