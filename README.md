# fast-track-dados

Projeto do desafio de Engenharia de Dados da Compass UOL (FT03 – Projeto 1).

## Cenário do projeto

O projeto construirá um panorama da produção científica brasileira indexada pelo OpenAlex: sua evolução ao longo do tempo, distribuição por instituições e localização (municípios, estados e regiões) e áreas de pesquisa. O pipeline cruzará duas APIs públicas de domínios distintos e trabalhará com respostas JSON.

### Fontes de dados

| Fonte | Domínio | Dados utilizados |
|---|---|---|
| [OpenAlex API](https://help.openalex.org/api/) | Produção científica | Trabalhos, ano de publicação, tópicos, citações, acesso aberto e afiliações/instituições |
| [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades) | Geografia oficial | Códigos e hierarquia de municípios, estados e regiões brasileiras |

O período será definido com base nos anos completos disponíveis no OpenAlex; o ano mais recente poderá ser excluído se ainda estiver incompleto. Serão considerados trabalhos com pelo menos uma afiliação brasileira. A associação geográfica será feita a partir dos metadados de localização das instituições no OpenAlex e normalizada com os códigos do IBGE; registros sem correspondência serão identificados no relatório de qualidade, não descartados silenciosamente.

### Pergunta e indicadores

**Pergunta:** como evoluiu a produção científica associada a instituições brasileiras e como ela se distribui entre instituições, municípios, estados, regiões e áreas de pesquisa?

- **Produção nacional por ano:** número de trabalhos distintos com pelo menos uma afiliação brasileira.
- **Distribuição geográfica:** trabalhos distintos associados a cada município, estado e região, além da participação de cada localidade no total nacional.
- **Produção por instituição:** número de trabalhos distintos associados a cada instituição brasileira por ano.
- **Evolução e áreas de pesquisa:** variação anual da produção e sua distribuição pelos tópicos classificados pelo OpenAlex.
- **Acesso aberto e citações:** proporção de trabalhos em acesso aberto e contagem de citações como métricas descritivas, não como medidas isoladas de qualidade.

Os indicadores representam a produção indexada pelo OpenAlex, não toda a pesquisa realizada no país. Um trabalho com afiliações em mais de um município, estado ou região será contado em cada localidade correspondente; por isso, os totais geográficos não são necessariamente somáveis ao total nacional. As localizações podem estar ausentes ou imprecisas. Volume de publicações, tópicos e citações não medem, por si só, qualidade acadêmica, qualidade do ensino universitário ou impacto de políticas de incentivo.

O escopo mede produção científica vinculada a instituições brasileiras em todas as áreas, incluindo educação quando identificada pelos tópicos do OpenAlex. Não mede financiamento ou incentivos à pesquisa: essa análise exigiria uma fonte adicional específica, com dados programáticos e cobertura verificáveis.

### Fluxo proposto

1. Consultar a API do OpenAlex com filtros de país e período, obtendo trabalhos e afiliações com paginação.
2. Consultar a API de Localidades do IBGE para obter códigos e hierarquias geográficas oficiais.
3. Desaninhar as afiliações, padronizar datas, identificadores e localidades; registrar associações não resolvidas.
4. Deduplicar por identificador de trabalho e agregar a produção por ano, instituição e localidade.
5. Cruzar as localidades com a hierarquia do IBGE, calcular indicadores e validar schema, nulidade, unicidade e intervalos.
6. Exportar o relatório de qualidade e salvar os dados finais em Parquet particionado por ano.

A API de Localidades do IBGE é pública. O OpenAlex permite consultas sem chave dentro de um orçamento compartilhado limitado; para execução reproduzível, recomenda-se configurar uma chave própria por meio da variável de ambiente `OPENALEX_API_KEY`. Credenciais nunca devem ser versionadas.

## Requisitos técnicos do desafio

O desafio propõe a construção de um pipeline de extração, transformação e disponibilização de dados usando Python e SQL, com foco em organização, qualidade, resiliência e reprodutibilidade.

### Extração de dados e APIs

- Consumir dados de pelo menos duas APIs públicas de domínios distintos, conforme o cenário acima.
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
