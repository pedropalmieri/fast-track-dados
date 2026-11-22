"""Configurações explícitas para repetir a coleta sem alterar o código."""

import os
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Config:
    start_year: int = date.today().year - 3
    end_year: int = date.today().year - 1
    max_pages: int = 1
    per_page: int = 100
    interval: float = 1.0

    def validate(self) -> None:
        if not 1900 <= self.start_year <= self.end_year < date.today().year:
            raise ValueError("Informe anos completos, entre 1900 e o ano anterior.")
        if self.max_pages < 1 or not 1 <= self.per_page <= 100 or self.interval < 0:
            raise ValueError("Páginas >= 1, tamanho entre 1 e 100 e intervalo >= 0.")
        if self.max_pages > 1 and not os.getenv("OPENALEX_API_KEY"):
            raise ValueError("Mais de uma página exige OPENALEX_API_KEY no ambiente.")
