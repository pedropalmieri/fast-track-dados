# fast-track-dados

Projeto do desafio de Engenharia de Dados da Compass UOL (FT03 – Projeto 1).

## Visão geral

O desafio propõe a construção de um pipeline de extração, transformação e disponibilização de dados usando Python e SQL. O objetivo é simular cenários reais de Engenharia de Dados, com foco em organização, qualidade, resiliência e reprodutibilidade.

## Requisitos técnicos

### Extração de dados e APIs

- Consumir dados de pelo menos duas APIs públicas de domínios distintos.
- Implementar controle de taxa de requisições (rate limiting), retentativas e tratamento de erros.
- Gerenciar credenciais por variáveis de ambiente (por exemplo, com `.env` ou `os.getenv`) e não versionar chaves de API.

### Transformação e SQL

- Organizar o código em scripts e funções modulares em Python, com type hints.
- Usar SQL para desaninhar coleções complexas, como arrays e JSONs aninhados, por exemplo com `UNNEST` ou ferramentas como DuckDB, SQLite ou PySpark.
- Aplicar pelo menos cinco transformações estruturadas, incluindo:
  - padronização de tipos e datas;
  - tratamento de valores nulos;
  - deduplicação;
  - cruzamento de fontes com `JOIN`;
  - enriquecimento de métricas.

### Qualidade e persistência dos dados

- Automatizar verificações de schema, proporção de valores nulos (null ratio), unicidade e intervalos.
- Exportar um resumo da execução e da auditoria de qualidade em JSON ou CSV.
- Salvar os dados finais em formato colunar (Parquet ou Delta Lake), com compressão Snappy.
- Particionar os arquivos por uma estratégia temporal adequada, como ano e mês.

## Entregáveis esperados

| Entregável | Requisito |
|---|---|
| Repositório Git | Código versionado, organizado de forma modular em `src/` e publicado no GitHub |
| Documentação | Instruções de execução, variáveis de ambiente e documentação das APIs neste README |
| Dependências | `requirements.txt` com as bibliotecas necessárias para reproduzir o projeto |
| Execução | Script `run.sh` ou um comando único para executar o pipeline ponta a ponta |
| Dataset persistido | Dados limpos em arquivos Parquet na pasta `output/` |
| Relatório de qualidade | Resultado das validações e métricas de consistência em JSON ou CSV |

## Critérios de avaliação

- **Engenharia de software:** clareza do código, organização do repositório e reprodutibilidade.
- **Qualidade técnica:** manipulação de estruturas de dados, eficiência das transformações e uso de SQL.
- **Robustez:** tratamento de exceções em requisições HTTP e resiliência a falhas.
- **Governança:** validação de schema, integridade dos dados e relatório de qualidade descritivo.

## Entrega

O repositório público no GitHub deve ser enviado pelo formulário disponibilizado durante a apresentação até **23/11/2026, às 08h00**.

## Especificação original

Consulte o [PDF do desafio](desafio/FT03_Engenharia_PRJ01_Python.pdf) para ver as diretrizes completas.
