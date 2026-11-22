"""Coleta pequena por padrão, com metadados para não confundir recorte com censo."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.config import Config
from src.http_client import HttpClient

OPENALEX = "https://api.openalex.org"
IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect(config: Config, directory: Path) -> dict:
    config.validate()
    client = HttpClient(config.interval)
    auth = {"api_key": os.environ["OPENALEX_API_KEY"]} if os.getenv("OPENALEX_API_KEY") else {}
    works: list[dict] = []
    coverage = []
    for year in range(config.start_year, config.end_year + 1):
        cursor = "*"
        fetched = 0
        total = None
        for _ in range(config.max_pages):
            page = client.get(f"{OPENALEX}/works", {
                **auth, "filter": f"institutions.country_code:br,publication_year:{year}",
                "sort": "publication_date:asc", "per_page": config.per_page, "cursor": cursor,
                "select": "id,display_name,publication_year,publication_date,cited_by_count,open_access,primary_topic,authorships",
            })
            if not isinstance(page.get("results"), list) or "count" not in page.get("meta", {}):
                raise ValueError("Resposta de trabalhos fora do contrato esperado.")
            total = page["meta"]["count"]
            works.extend(page["results"])
            fetched += len(page["results"])
            cursor = page["meta"].get("next_cursor")
            if not cursor or not page["results"] or fetched >= total:
                break
        coverage.append({"year": year, "available": total, "fetched": fetched,
                         "complete": fetched >= total})
    if not works:
        raise ValueError("Nenhum trabalho retornado; não será gerada uma entrega vazia.")
    # Listagens cortam autores após 100 posições; a afiliação brasileira pode vir depois.
    # Consulto o trabalho individual para não perder essas instituições no JOIN.
    expanded = 0
    for work in works:
        if len(work.get("authorships", [])) >= 100:
            work_id = work["id"].rsplit("/", 1)[-1]
            detail = client.get(f"{OPENALEX}/works/{work_id}", auth)
            work["authorships"] = detail["authorships"]
            expanded += 1
    ids = sorted({i["id"].rsplit("/", 1)[-1] for w in works
                  for a in w.get("authorships", []) for i in a.get("institutions", [])
                  if i.get("country_code") == "BR" and i.get("id")})
    institutions = []
    for offset in range(0, len(ids), 50):
        page = client.get(f"{OPENALEX}/institutions", {
            **auth, "filter": "openalex_id:" + "|".join(ids[offset:offset + 50]),
            "per_page": 50, "select": "id,display_name,country_code,geo",
        })
        institutions.extend(page["results"])
    municipalities = client.get(IBGE)
    if not isinstance(municipalities, list) or not municipalities:
        raise ValueError("IBGE não retornou a lista de municípios.")
    for name, value in [("works", works), ("institutions", institutions), ("municipalities", municipalities)]:
        save_json(directory / f"{name}.json", value)
    manifest = {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": [OPENALEX, IBGE], "start_year": config.start_year, "end_year": config.end_year,
        "selection": "publication_date:asc; páginas limitadas por ano; recorte não probabilístico",
        "coverage": coverage, "complete": all(c["complete"] for c in coverage),
        "expanded_authorships": expanded, "requested_institutions": len(ids), "returned_institutions": len(institutions),
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(directory.glob("*.json")) if p.name != "manifest.json"},
    }
    save_json(directory / "manifest.json", manifest)
    return manifest
