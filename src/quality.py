"""Verificações pequenas e explícitas, sem esconder problemas da coleta."""

import duckdb


TABLE_KEYS = {
    "works": ["work_id"],
    "production": ["work_id", "institution_id"],
    "annual": ["year"],
    "institution_annual": ["year", "institution_id"],
    "geography": ["year", "level", "location_id"],
    "topics": ["year", "topic"],
}


def audit(connection: duckdb.DuckDBPyConnection, manifest: dict) -> dict:
    checks: list[dict] = []

    def check(name: str, invalid: int, severity: str = "error") -> None:
        checks.append({"name": name, "invalid_rows": invalid,
                       "passed": invalid == 0, "severity": severity})

    def scalar(query: str, params: list | None = None) -> int:
        return connection.execute(query, params or []).fetchone()[0]

    # O schema esperado inclui os tipos, além dos nomes das colunas.
    schema = dict((row[0], row[1]) for row in connection.execute("DESCRIBE production").fetchall())
    expected = {"work_id": "VARCHAR", "year": "INTEGER", "publication_date": "DATE",
                "citations": "BIGINT", "is_oa": "BOOLEAN", "institution_id": "VARCHAR",
                "municipality_id": "BIGINT", "geo_status": "VARCHAR"}
    check("schema_production", sum(schema.get(name) != kind for name, kind in expected.items()))
    tables = {}
    for table, keys in TABLE_KEYS.items():
        count = scalar(f"SELECT count(*) FROM {table}")
        check(f"{table}_not_empty", int(count == 0))
        grouped = ", ".join(keys)
        duplicates = scalar(f"SELECT coalesce(sum(n - 1), 0)::BIGINT FROM "
                            f"(SELECT count(*) n FROM {table} GROUP BY {grouped} HAVING count(*) > 1)")
        check(f"{table}_unique_key", duplicates)
        columns = connection.execute(f"DESCRIBE {table}").fetchall()
        null_ratios = {}
        for name, _type, *_ in columns:
            nulls = scalar(f'SELECT count(*) FROM {table} WHERE "{name}" IS NULL')
            null_ratios[name] = nulls / count if count else None
            if name in keys:
                check(f"{table}_{name}_not_null", nulls)
        tables[table] = {"rows": count, "null_ratio": null_ratios}

    start, end = manifest["start_year"], manifest["end_year"]
    check("year_in_requested_range", scalar(
        "SELECT count(*) FROM works WHERE year IS NULL OR year NOT BETWEEN ? AND ?", [start, end]))
    check("valid_publication_date", scalar(
        "SELECT count(*) FROM works WHERE publication_date IS NULL OR year(publication_date) != year"))
    check("non_negative_citations", scalar("SELECT count(*) FROM works WHERE citations < 0"))
    check("all_works_have_brazilian_affiliation", scalar(
        "SELECT count(*) FROM works w WHERE NOT EXISTS "
        "(SELECT 1 FROM affiliations a WHERE a.work_id = w.work_id)"))
    check("municipality_unique_id", scalar(
        "SELECT count(*) - count(DISTINCT municipality_id) FROM municipalities"))
    check("municipality_hierarchy_present", scalar(
        "SELECT count(*) FROM municipalities WHERE municipality_id IS NULL "
        "OR municipality IS NULL OR state_code IS NULL OR region IS NULL"))
    check("geographic_join_preserves_affiliations", abs(
        scalar("SELECT count(*) FROM affiliations") - scalar("SELECT count(*) FROM production")))
    check("annual_totals_match_works", abs(
        scalar("SELECT sum(works_count)::BIGINT FROM annual") - scalar("SELECT count(*) FROM works")))
    check("shares_in_range", scalar(
        "SELECT count(*) FROM geography WHERE share_of_collected_works NOT BETWEEN 0 AND 1"))
    check("source_total_covers_collected_works", scalar(
        "SELECT count(*) FROM annual WHERE source_available_works < works_count"))
    check("collection_coverage_in_range", scalar(
        "SELECT count(*) FROM annual WHERE collection_coverage NOT BETWEEN 0 AND 1"))
    check("oa_share_in_range", scalar(
        "SELECT count(*) FROM annual WHERE oa_share NOT BETWEEN 0 AND 1"))
    # Ausências opcionais são medidas, mas não viram zero para melhorar o relatório.
    check("missing_citations", scalar("SELECT count(*) FROM works WHERE citations IS NULL"), "warning")
    check("missing_open_access", scalar("SELECT count(*) FROM works WHERE is_oa IS NULL"), "warning")
    check("unmatched_geography", scalar(
        "SELECT count(*) FROM production WHERE municipality_id IS NULL"), "warning")
    check("incomplete_collection", int(not manifest["complete"]), "warning")
    missing_institutions = manifest["requested_institutions"] - manifest["returned_institutions"]
    check("institutions_not_returned", max(0, missing_institutions), "warning")
    unmatched = connection.execute(
        "SELECT DISTINCT institution_id, institution_name, city_source, state_source, geo_status "
        "FROM production WHERE municipality_id IS NULL ORDER BY institution_id").fetchall()
    passed = all(c["passed"] for c in checks if c["severity"] == "error")
    return {
        "status": "passed" if passed else "failed", "checks": checks, "tables": tables,
        "duplicates_removed": scalar("SELECT count(*) FROM raw_works") - tables["works"]["rows"],
        "unmatched_institutions": [dict(zip(
            ["institution_id", "institution_name", "city", "state", "reason"], row)) for row in unmatched],
        "source_manifest": manifest,
        "limitations": ["Recorte não probabilístico quando complete=false; indicadores do recorte não estimam o país.",
                        "Totais nacionais usam meta.count da API; demais indicadores usam trabalhos coletados.",
                        "Participações geográficas usam os trabalhos coletados como denominador.",
                        "Um trabalho pode contar em mais de uma localidade; totais não são somáveis.",
                        "Citações são observadas na coleta e favorecem trabalhos mais antigos.",
                        "Localização da instituição não identifica o campus de cada autor."],
    }
