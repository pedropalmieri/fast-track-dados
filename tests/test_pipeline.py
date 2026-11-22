"""Dados inventados e pequenos para conferir as regras de contagem e qualidade."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.extract import save_json
from src.persist import export
from src.pipeline import load_manifest
from src.quality import audit
from src.transform import transform


def institution(identifier: str) -> dict:
    return {"id": identifier, "display_name": identifier, "country_code": "BR"}


def work(identifier: str, year: int, institutions: list[str]) -> dict:
    return {"id": identifier, "display_name": "Trabalho de teste", "publication_year": year,
            "publication_date": f"{year}-01-02", "cited_by_count": 10,
            "open_access": {"is_oa": True}, "primary_topic": None,
            "authorships": [{"institutions": [institution(i) for i in institutions]}]}


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raw = Path(self.temp.name) / "raw"
        # I1 e I4 ficam na mesma cidade; I2 fica em uma cidade homônima de outra UF.
        institutions = [{**institution(i), "geo": {"city": city, "region": state}}
                        for i, city, state in [("I1", "Sao Teste", "SP"), ("I2", "São Teste", "RJ"),
                                               ("I3", "Sem cadastro", "SP"), ("I4", "São Teste", "SP")]]
        municipalities = [{"id": code, "nome": "São Teste", "regiao-imediata": {
            "regiao-intermediaria": {"UF": {"sigla": uf, "nome": state,
                                               "regiao": {"nome": "Sudeste"}}}}}
                          for code, uf, state in [(1, "SP", "São Paulo"), (2, "RJ", "Rio de Janeiro")]]
        first = work("W1", 2023, ["I1", "I1", "I2", "I4"])
        save_json(self.raw / "works.json", [first, first, work("W2", 2024, ["I1", "I3"])])
        save_json(self.raw / "institutions.json", institutions)
        save_json(self.raw / "municipalities.json", municipalities)
        self.manifest = {"start_year": 2023, "end_year": 2024, "complete": False,
                         "requested_institutions": 4, "returned_institutions": 4}

    def connection(self):
        connection = transform(self.raw)
        self.addCleanup(connection.close)
        return connection

    def test_deduplication_and_distinct_geographic_counts(self) -> None:
        c = self.connection()
        self.assertEqual(c.execute("SELECT count(*) FROM works").fetchone()[0], 2)
        self.assertEqual(c.execute("SELECT count(*) FROM production").fetchone()[0], 5)
        self.assertEqual(c.execute("SELECT works_count FROM geography WHERE year=2023 "
                                   "AND level='municipio' AND location_id='1'").fetchone()[0], 1)
        self.assertEqual(c.execute("SELECT sum(citations) FROM annual").fetchone()[0], 20)
        self.assertEqual(c.execute("SELECT count(*) FROM geography WHERE year=2023 "
                                   "AND level='municipio'").fetchone()[0], 2)

    def test_unmatched_city_is_preserved_and_reported(self) -> None:
        report = audit(self.connection(), self.manifest)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["duplicates_removed"], 1)
        self.assertEqual(len(report["unmatched_institutions"]), 1)
        self.assertEqual(report["tables"]["production"]["null_ratio"]["municipality_id"], 0.2)

    def test_invalid_dates_prevent_parquet_publication(self) -> None:
        data = json.loads((self.raw / "works.json").read_text())
        data[2]["publication_date"] = "data inválida"
        save_json(self.raw / "works.json", data)
        c = self.connection()
        report = audit(c, self.manifest)
        self.assertEqual(report["status"], "failed")
        destination = Path(self.temp.name) / "failed"
        with self.assertRaises(ValueError):
            export(c, destination, report)
        self.assertFalse(list(destination.rglob("*.parquet")))
        self.assertTrue((destination / "quality_report.json").exists())

    def test_unknown_oa_and_citations_are_not_converted_to_zero(self) -> None:
        data = json.loads((self.raw / "works.json").read_text())
        data[2]["open_access"] = None
        data[2]["cited_by_count"] = None
        save_json(self.raw / "works.json", data)
        c = self.connection()
        self.assertEqual(c.execute("SELECT oa_share, citations FROM annual WHERE year=2024").fetchone(),
                         (None, None))
        self.assertEqual(audit(c, self.manifest)["status"], "passed")

    def test_export_roundtrip_and_year_partition(self) -> None:
        c = self.connection()
        destination = Path(self.temp.name) / "output"
        export(c, destination, audit(c, self.manifest))
        self.assertTrue((destination / "production/year=2023/data_0.parquet").exists())
        self.assertEqual(c.execute("SELECT count(*) FROM read_parquet(?, hive_partitioning=true)",
                                  [str(destination / "production/**/*.parquet")]).fetchone()[0], 5)

    def test_modified_raw_file_fails_integrity_check(self) -> None:
        manifest = {**self.manifest, "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                               for p in self.raw.glob("*.json")}}
        save_json(self.raw / "manifest.json", manifest)
        self.assertEqual(load_manifest(self.raw)["start_year"], 2023)
        (self.raw / "works.json").write_text("[]")
        with self.assertRaises(ValueError):
            load_manifest(self.raw)


if __name__ == "__main__":
    unittest.main()
