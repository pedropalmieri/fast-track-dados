"""DuckDB executa o desaninhamento e as transformações sem servidor externo."""

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def transform(raw: Path) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    schemas = {
        "works": {"id": "VARCHAR", "display_name": "VARCHAR", "publication_year": "VARCHAR",
                  "publication_date": "VARCHAR", "cited_by_count": "VARCHAR",
                  "open_access": "JSON", "primary_topic": "JSON", "authorships": "JSON"},
        "institutions": {"id": "VARCHAR", "display_name": "VARCHAR", "country_code": "VARCHAR", "geo": "JSON"},
        "municipalities": {"id": "BIGINT", "nome": "VARCHAR", "regiao-imediata": "JSON"},
    }
    try:
        for name, columns in schemas.items():
            relation = connection.read_json(str(raw / f"{name}.json"), columns=columns, format="array")
            relation.create(f"raw_{name}")
        # O total do filtro vem do manifesto, não do tamanho da página baixada.
        connection.execute("CREATE TABLE raw_coverage (year INTEGER, available BIGINT, fetched BIGINT, complete BOOLEAN)")
        manifest_path = raw / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            rows = [(c["year"], c["available"], c["fetched"], c["complete"])
                    for c in manifest.get("coverage", [])]
            if rows:
                connection.executemany("INSERT INTO raw_coverage VALUES (?, ?, ?, ?)", rows)
        connection.execute((ROOT / "sql/transform.sql").read_text(encoding="utf-8"))
        return connection
    except Exception:
        connection.close()
        raise
