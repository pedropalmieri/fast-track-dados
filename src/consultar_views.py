"""Consulta as views da entrega pelo SQL Warehouse, usando o login local da CLI."""

import argparse
import json
import os
import subprocess
import sys


ORDENACAO = {
    "annual": "year",
    "production": "year, work_id, institution_id",
    "institution_annual": "year, works_count DESC, institution_id",
    "geography": "year, level, works_count DESC, location_id",
    "topics": "year, works_count DESC, topic",
}


def _cli(profile: str, *args: str) -> dict | list:
    try:
        result = subprocess.run(
            ["databricks", *args, "--profile", profile, "--output", "json"],
            check=True, capture_output=True, text=True, timeout=80,
        )
    except FileNotFoundError:
        raise RuntimeError("Instale a Databricks CLI e confirme com `databricks version`.") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError("A CLI excedeu o tempo de espera. Confira o estado do warehouse.") from None
    except subprocess.CalledProcessError:
        raise RuntimeError(
            "A CLI recusou a chamada. Confira o login com `databricks auth profiles`, "
            "a conexão e a permissão de uso do warehouse."
        ) from None
    return json.loads(result.stdout)


def consultar(view: str, *, ano: int | None = None, limite: int = 20,
              profile: str = "fast-track", warehouse_id: str | None = None) -> list[dict]:
    """Retorna registros da view. A API entrega valores como texto ou None."""
    if view not in ORDENACAO or type(limite) is not int or not 1 <= limite <= 100:
        raise ValueError("Escolha uma view da entrega e um limite entre 1 e 100.")
    if ano is not None and type(ano) is not int:
        raise ValueError("O ano deve ser inteiro.")
    if not warehouse_id:
        warehouses = _cli(profile, "warehouses", "list")
        if len(warehouses) != 1:
            raise ValueError("Defina DATABRICKS_WAREHOUSE_ID para selecionar o warehouse.")
        warehouse_id = warehouses[0]["id"]

    filtro = " WHERE year = :ano" if ano is not None else ""
    payload = {
        "warehouse_id": warehouse_id,
        "statement": (f"SELECT * FROM workspace.fast_track_dados.{view}{filtro} "
                      f"ORDER BY {ORDENACAO[view]} LIMIT {limite}"),
        "parameters": [] if ano is None else [{"name": "ano", "type": "INT", "value": str(ano)}],
        "wait_timeout": "50s",
        "on_wait_timeout": "CANCEL",
    }
    response = _cli(profile, "api", "post", "/api/2.0/sql/statements", "--json", json.dumps(payload))
    status = response["status"]
    if status["state"] != "SUCCEEDED":
        detail = status.get("error", {}).get("message") or "Confira se o warehouse está ativo."
        raise RuntimeError(f"Consulta {status['state']}: {detail}")
    columns = [c["name"] for c in response["manifest"]["schema"]["columns"]]
    return [dict(zip(columns, row, strict=True)) for row in response["result"].get("data_array", [])]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("view", choices=ORDENACAO)
    parser.add_argument("--ano", type=int)
    parser.add_argument("--limite", type=int, default=20)
    args = parser.parse_args()
    try:
        rows = consultar(args.view, ano=args.ano, limite=args.limite,
                         profile=os.getenv("DATABRICKS_CONFIG_PROFILE") or "fast-track",
                         warehouse_id=os.getenv("DATABRICKS_WAREHOUSE_ID"))
    except (ValueError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 1
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
