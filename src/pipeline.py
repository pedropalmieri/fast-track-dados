"""Comando de entrada: coleta, transforma, audita e salva a entrega."""

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.config import Config
from src.extract import collect, save_json
from src.persist import export
from src.quality import audit
from src.transform import transform

LOGGER = logging.getLogger(__name__)


def load_manifest(raw: Path) -> dict:
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    # Confiro os três nomes esperados; não uso caminhos fornecidos pelo manifesto.
    for name in ("works.json", "institutions.json", "municipalities.json"):
        digest = hashlib.sha256((raw / name).read_bytes()).hexdigest()
        if digest != manifest["sha256"].get(name):
            raise ValueError(f"Arquivo alterado ou incompleto: {name}.")
    return manifest


def main() -> int:
    defaults = Config()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=defaults.start_year)
    parser.add_argument("--end-year", type=int, default=defaults.end_year)
    parser.add_argument("--max-pages", type=int, default=defaults.max_pages)
    parser.add_argument("--per-page", type=int, default=defaults.per_page)
    parser.add_argument("--interval", type=float, default=defaults.interval)
    parser.add_argument("--from-raw", type=Path, help="Reprocessa coleta local sem acessar APIs.")
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:6]
    destination = args.output / "runs" / run_id
    connection = None
    try:
        if args.from_raw:
            raw = args.from_raw
            LOGGER.info("Reprocessando arquivos locais e verificando integridade.")
        else:
            raw = Path("data/raw") / run_id
            LOGGER.info("Coletando OpenAlex e IBGE; isso pode levar alguns minutos.")
            collect(Config(args.start_year, args.end_year, args.max_pages, args.per_page, args.interval), raw)
        manifest = load_manifest(raw)
        connection = transform(raw)
        report = audit(connection, manifest)
        report["run_id"] = run_id
        report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        export(connection, destination, report)
        # Só atualizo o apontador após todas as tabelas serem gravadas e relidas.
        pointer = args.output / f".latest-{run_id}.json"
        save_json(pointer, {"run_id": run_id, "path": f"runs/{run_id}"})
        pointer.replace(args.output / "latest.json")
        LOGGER.info("Entrega aprovada: %s", destination)
        warnings = [c["name"] for c in report["checks"] if c["severity"] == "warning" and not c["passed"]]
        if warnings:
            LOGGER.warning("Consulte os avisos no relatório: %s", ", ".join(warnings))
        return 0
    except Exception as error:
        # Mensagens de bibliotecas podem conter URLs autenticadas ou dados brutos.
        # Registro somente a classe; a auditoria detalhada fica no relatório quando disponível.
        save_json(destination / "failure.json", {"run_id": run_id, "status": "failed",
                                                "error_type": type(error).__name__})
        LOGGER.error("Execução interrompida (%s). Consulte %s.", type(error).__name__, destination)
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
