"""Primeiro marco da migracao: production no SQL Warehouse, com paridade local."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from src.config import Config
from src.consultar_views import _cli
from src.extract import collect, save_json
from src.pipeline import load_manifest
from src.transform import ROOT, transform

SCHEMA = "workspace.fast_track_piloto"
CHAVES = "work_id, institution_id, municipality_id, state_code, region, geo_status"


def executar(raw: Path | None = None) -> dict:
    run = uuid4().hex[:12]
    if raw is None:
        raw = Path("data/raw") / f"piloto_{run}"
        collect(Config(2023, 2025), raw)
    manifest = load_manifest(raw)
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE") or "fast-track"
    warehouse = os.getenv("DATABRICKS_WAREHOUSE_ID")
    if not warehouse:
        warehouses = _cli(profile, "warehouses", "list")
        if len(warehouses) != 1:
            raise ValueError("Selecione DATABRICKS_WAREHOUSE_ID.")
        warehouse = warehouses[0]["id"]

    def sql(statement: str) -> list:
        payload = {"statement": statement, "warehouse_id": warehouse,
                   "wait_timeout": "50s", "on_wait_timeout": "CANCEL"}
        result = _cli(profile, "api", "post", "/api/2.0/sql/statements", "--json", json.dumps(payload))
        if result["status"]["state"] != "SUCCEEDED":
            raise RuntimeError(result["status"])
        if result.get("manifest", {}).get("truncated"):
            raise RuntimeError("Resposta truncada: paridade nao verificada.")
        chunk = result.get("result", {})
        rows = list(chunk.get("data_array", []))
        while chunk.get("next_chunk_internal_link"):
            chunk = _cli(profile, "api", "get", chunk["next_chunk_internal_link"])
            rows.extend(chunk.get("data_array", []))
        return rows

    volume = f"/Volumes/workspace/fast_track_piloto/brutos/{run}"
    table = f"{SCHEMA}.production_{run}"
    sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    sql(f"CREATE VOLUME IF NOT EXISTS {SCHEMA}.brutos")
    dest = "dbfs:" + volume
    cli = ["databricks", "--profile", profile, "fs"]
    subprocess.run([*cli, "mkdir", dest], check=True)
    for name in ("works.json", "institutions.json", "municipalities.json", "manifest.json"):
        subprocess.run([*cli, "cp", str(raw / name), f"{dest}/{name}"], check=True)
    query = (ROOT / "sql/production_databricks.sql").read_text(encoding="utf-8")
    sql(f"CREATE TABLE {table} USING DELTA AS " + query.replace("{{raw}}", volume))

    with transform(raw) as db:
        local = Counter(tuple(str(v) if v is not None else None for v in row)
                        for row in db.execute(f"SELECT {CHAVES} FROM production").fetchall())
    remote = Counter(tuple(row) for row in sql(f"SELECT {CHAVES} FROM {table}"))
    keys = {row[:2] for row in remote}
    ok = bool(remote) and local == remote and len(keys) == remote.total()
    report = {"paridade": ok, "tabela": table, "volume": volume, "brutos_locais": str(raw),
              "sha256": manifest["sha256"], "pares": remote.total(),
              "trabalhos": len({r[0] for r in remote}), "instituicoes": len({r[1] for r in remote}),
              "linhas_so_duckdb": (local - remote).total(),
              "linhas_so_databricks": (remote - local).total()}
    path = Path("data/pilotos") / run / "paridade.json"
    save_json(path, report)
    if not ok:
        raise ValueError(f"Paridade reprovada: {path}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-raw", type=Path, help="Reusar coleta com manifesto e hashes.")
    print(json.dumps(executar(parser.parse_args().from_raw), ensure_ascii=False, indent=2))
