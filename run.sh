#!/usr/bin/env bash
# Entro na pasta do projeto para o comando funcionar de qualquer diretório.
set -euo pipefail
cd "$(dirname "$0")"

# O ambiente fica separado do Python usado por outros projetos.
if [ ! -x .venv/bin/python ]; then
    "${PYTHON:-python3}" -m venv .venv
fi
.venv/bin/python -m pip install --disable-pip-version-check --quiet -r requirements.txt
exec .venv/bin/python -m src.pipeline "$@"
