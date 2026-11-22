"""Publica uma pasta por execução; só dados aprovados recebem Parquet."""

from pathlib import Path

import duckdb

from src.extract import save_json

TABLES = ("production", "annual", "institution_annual", "geography", "topics")


def export(connection: duckdb.DuckDBPyConnection, directory: Path, report: dict) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    save_json(directory / "quality_report.json", report)
    if report["status"] != "passed":
        raise ValueError("Qualidade reprovada. Consulte quality_report.json; Parquet não foi publicado.")
    try:
        for table in TABLES:
            # O nome da tabela vem da lista fixa acima, não da entrada do usuário.
            destination = str((directory / table).resolve()).replace("'", "''")
            connection.execute(
                f"COPY {table} TO '{destination}' "
                "(FORMAT PARQUET, COMPRESSION SNAPPY, PARTITION_BY (year))")
            # Confiro também a leitura dos arquivos gravados, não apenas das tabelas em memória.
            files = str(directory / table / "**/*.parquet")
            actual = connection.execute("SELECT count(*) FROM read_parquet(?, hive_partitioning=true)",
                                        [files]).fetchone()[0]
            expected = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            if actual != expected:
                raise ValueError(f"Contagem divergente ao reler {table}.")
            codecs = connection.execute(
                "SELECT DISTINCT compression FROM parquet_metadata(?)", [files]).fetchall()
            if codecs != [("SNAPPY",)]:
                raise ValueError(f"Compressão inesperada em {table}.")
    except Exception:
        # Uma pasta incompleta permanece identificada como falha e nunca vira a última entrega válida.
        report["status"] = "failed_export"
        save_json(directory / "quality_report.json", report)
        raise
