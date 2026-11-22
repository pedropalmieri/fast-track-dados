"""Cliente compartilhado: limita chamadas e repete somente falhas transitórias."""

import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests


class ApiError(RuntimeError):
    """Erro público sem URL, parâmetros ou credenciais na mensagem."""


class HttpClient:
    def __init__(self, interval: float = 1.0, attempts: int = 4) -> None:
        self.interval = interval
        self.attempts = attempts
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "fast-track-dados/1.0 (educational pipeline)"
        self.last_request = 0.0

    def get(self, url: str, params: dict | None = None) -> Any:
        for attempt in range(self.attempts):
            time.sleep(max(0.0, self.interval - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            response = None
            try:
                response = self.session.get(url, params=params, timeout=(10, 60))
                if response.status_code != 429 and response.status_code < 500:
                    if not response.ok:
                        raise ApiError(f"API recusou a consulta: HTTP {response.status_code}.")
                    try:
                        return response.json()
                    except ValueError:
                        raise ApiError("API retornou conteúdo que não é JSON.") from None
            except (requests.Timeout, requests.ConnectionError):
                pass
            except requests.RequestException:
                raise ApiError("Falha de comunicação com a API.") from None
            if attempt + 1 == self.attempts:
                raise ApiError("Limite de tentativas atingido; coleta interrompida.") from None
            delay = float(2 ** attempt)
            if response is not None:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    try:
                        retry_date = parsedate_to_datetime(retry_after)
                        delay = max(delay, (retry_date - datetime.now(timezone.utc)).total_seconds())
                    except (ValueError, TypeError):
                        pass
            time.sleep(delay)
