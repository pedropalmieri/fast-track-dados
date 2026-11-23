# Produção científica brasileira com Python e SQL

Desafio FT03 - Projeto 1, como prática após a **Trilha Engenharia de Dados POD TILLER**, disponibilizada pela Compass UOL na Udemy.

A ideia é olhar para os trabalhos ligados a instituições brasileiras: como a contagem muda por ano e onde aparecem as instituições, cidades e temas de pesquisa. Para isso, juntei dados do OpenAlex com os municípios do IBGE.

O projeto já tem coleta, tratamento em SQL, testes, relatório de qualidade e arquivos Parquet em `output/`.

Para acompanhar a implementação por arquivo e por linhas, leia o [guia passo a passo](GUIA_PASSO_A_PASSO.md). Ele explica as escolhas, os comandos, os testes e as colunas da entrega.

O [README das APIs](docs/apis/README.md) traz as chamadas, os JSONs esperados, o cruzamento entre as fontes e a diferença entre o que o desafio pediu e a escolha de salvar indicadores em Parquet.

A [apresentação do desafio](APRESENTACAO_DESAFIO.md) conta em primeira pessoa como o projeto foi resolvido: a ideia inicial, a coleta, os arquivos criados, os tratamentos, os problemas e os resultados.

## Por que essas APIs?

Mantive a proposta inicial do repositório. O OpenAlex tem autores e instituições dentro de listas, o que permite praticar o desaninhamento em SQL. O IBGE entra com os códigos oficiais de município, estado e região. As duas fontes têm papéis diferentes e uma ligação que dá para explicar e conferir.

Usei DuckDB porque ele roda junto com o Python, lê JSON e grava Parquet. Assim não precisei montar um banco ou um serviço à parte só para este desafio.

| Fonte | O que busco | Documentação |
|---|---|---|
| OpenAlex | Trabalhos, afiliações, localização das instituições e total do filtro por ano | [API](https://help.openalex.org/api/) |
| IBGE | Municípios e sua ligação com UFs e regiões | [Localidades](https://servicodados.ibge.gov.br/api/docs/localidades) |

## Por que usei SQL?

O item 2.2 do [enunciado](desafio/FT03_Engenharia_PRJ01_Python.pdf) pede desaninhar coleções complexas usando SQL. No OpenAlex, cada trabalho tem uma lista de autores, e cada autor pode ter uma lista de instituições. Usei `json_each` no DuckDB para abrir essas listas em linhas.

Depois, usei SQL para remover afiliações repetidas, converter tipos, cruzar cidade e UF com o IBGE e calcular as contagens. Por exemplo: se dois autores de um trabalho são da mesma instituição, esse trabalho deve contar uma vez para ela, não duas.

Python cuida das chamadas às APIs, dos arquivos e da ordem das etapas. O SQL trata e consulta os dados depois da coleta. O DuckDB executa essas consultas dentro do programa Python, sem um servidor de banco separado. Seria possível tratar os JSONs só com Python, mas isso não atenderia ao requisito de SQL do desafio.

## O que a análise cobre

A execução entregue usa 2023, 2024 e 2025. São anos encerrados, mas a base ainda pode receber correções e novos registros desses períodos.

Há dois conjuntos de números, e essa diferença é importante:

- **Total nacional indexado:** vem de `meta.count`, a contagem do filtro brasileiro que o OpenAlex informa para cada ano.
- **Dados coletados:** 100 trabalhos por ano, ordenados por data de publicação crescente. Instituições, geografia, temas, citações e acesso aberto são calculados apenas nesses 300 trabalhos.

Esse recorte não é aleatório nem representa toda a pesquisa brasileira. A ordenação favorece o começo do ano e pode incluir datas preenchidas como 1º de janeiro. Não use os rankings do recorte como ranking nacional.

Veja os números e a leitura dos resultados em [RESULTADOS.md](RESULTADOS.md).

## Como rodar

Testado com Python 3.13. É preciso ter Git, Python com suporte a `venv` e internet para instalar as bibliotecas e consultar as APIs.

```bash
git clone https://github.com/pedropalmieri/fast-track-dados.git
cd fast-track-dados
./run.sh
```

O script cria `.venv`, instala as versões de `requirements.txt` e executa o pipeline. Por padrão, usa os três anos anteriores ao ano atual, com uma página de 100 trabalhos por ano. Para repetir o período desta entrega:

```bash
./run.sh --start-year 2023 --end-year 2025 --max-pages 1 --per-page 100
```

Não é preciso ativar o ambiente para usar `run.sh`. Se ele já estiver preparado, também dá para executar direto:

```bash
.venv/bin/python -m src.pipeline --start-year 2023 --end-year 2025
```

### Chave do OpenAlex

A consulta pequena funcionou sem chave na execução de 22/11/2026. Nesse caso, o orçamento de uso é compartilhado pelo IP. Para seguir o cursor além da primeira página, configure sua chave gratuita no ambiente:

```bash
export OPENALEX_API_KEY='sua-chave'
./run.sh --start-year 2023 --end-year 2025 --max-pages 5
```

A chave é lida com `os.getenv` e não deve entrar no Git. O projeto não carrega `.env` automaticamente. Se você usar esse arquivo por conta própria, ele já está no `.gitignore`. O IBGE não precisa de chave.

Mais páginas aumentam o recorte; não garantem coleta completa. Confira `complete` e `coverage` no relatório. Veja as regras atuais de [autenticação](https://help.openalex.org/api/authentication/) e [paginação](https://help.openalex.org/api/paging/), pois os limites do serviço podem mudar.

### Reprocessar sem consultar as APIs

Os JSONs brutos ficam em `data/raw/<id-da-execucao>/`, fora do Git. Depois de uma coleta:

```bash
.venv/bin/python -m src.pipeline --from-raw data/raw/ID_DA_COLETA
```

Troque `ID_DA_COLETA` pela pasta gerada no seu computador. O comando confere os hashes dos arquivos antes de usar os dados. Os brutos da entrega não estão no repositório; os Parquets finais e o relatório estão. Uma nova consulta pode trazer números diferentes porque as APIs mudam.

### Transformar os brutos no Databricks SQL (piloto)

O primeiro marco da migração é a tabela `production`: Python coleta os três JSONs e o manifesto; o SQL Warehouse lê os arquivos do volume, desaninha as afiliações, deduplica por trabalho e instituição e cruza cidade e UF com o IBGE. O SQL está em [sql/production_databricks.sql](sql/production_databricks.sql). O DuckDB serve como referência para comparar o resultado sobre a mesma entrada.

Com as dependências de `requirements.txt`, a CLI autenticada como descrito abaixo e permissão de criar schema, volume e tabela no catálogo `workspace`, execute na raiz:

```bash
python3 -m src.piloto_databricks
```

O piloto coleta uma página de 100 trabalhos por ano de 2023 a 2025. Para usar os mesmos arquivos outra vez, passe `--from-raw data/raw/ID_DA_COLETA`. A cada execução o comando verifica os hashes locais e usa um destino novo: `/Volumes/workspace/fast_track_piloto/brutos/<id>` e a tabela Delta `workspace.fast_track_piloto.production_<id>`. A paridade exige pares únicos e compara os IDs de trabalho, instituição e município, a UF, região e o status geográfico, incluindo a multiplicidade das linhas. O resultado fica em `data/pilotos/<id>/paridade.json`.

Esta etapa não publica novos Parquets nem altera as cinco views da entrega original. Os quatro agregados e a auditoria de publicação ainda usam o fluxo original.

**Passo a passo da execução conferida**

| Etapa | O que foi feito | Como conferir |
|---|---|---|
| 1. Coleta em Python | Busquei 100 trabalhos por ano (2023 a 2025), as instituições e os municípios. | Na pasta local da coleta, `manifest.json` registra a cobertura de cada ano e os hashes dos três JSONs. |
| 2. Recebimento no Databricks | Enviei os JSONs e o manifesto para um volume separado da entrega original. | No Catalog Explorer, abra `workspace` → `fast_track_piloto` → volume `brutos` → pasta `e33804f6cb6e`. |
| 3. Transformação em SQL | Abri autores e instituições, mantive as afiliações brasileiras e cruzei cidade e UF com o IBGE. | A tabela Delta `workspace.fast_track_piloto.production_e33804f6cb6e` tem uma linha por trabalho e instituição. |
| 4. Comparação com a referência | Usei os mesmos brutos nos dois motores e comparei as chaves e a geografia, não apenas o total de linhas. | O relatório local `data/pilotos/e33804f6cb6e/paridade.json` registrou 592 pares, 300 trabalhos, 209 instituições e zero linhas exclusivas de cada motor. |

Para conferir a contagem da etapa 3 no SQL Editor:

```sql
SELECT COUNT(*) AS pares, COUNT(DISTINCT work_id) AS trabalhos,
       COUNT(DISTINCT institution_id) AS instituicoes
FROM workspace.fast_track_piloto.production_e33804f6cb6e;
```

Os 592 pares pertencem à nova coleta. Os 591 pares de `workspace.fast_track_dados.production` continuam sendo a referência da entrega original. A tabela do piloto não substitui essa view, e o relatório local não é versionado.

### Consultar as views no Databricks

Na raiz do repositório, use Python e a Databricks CLI autenticada para ler as views de `workspace.fast_track_dados` pelo SQL Warehouse. Essa integração é opcional: não executa o ETL, não publica arquivos e não precisa de chave do OpenAlex. As views refletem a entrega carregada no volume, não uma nova execução local.

```bash
python3 -m src.consultar_views annual
python3 -m src.consultar_views geography --ano 2025 --limite 10
```

Aceita `annual`, `production`, `institution_annual`, `geography` e `topics`. Retorna uma lista JSON com os nomes das colunas da view; a API representa valores não nulos como texto. Sem `--ano`, consulta todos os anos. O limite padrão é 20 linhas e o máximo por chamada é 100.

Em uma máquina nova, instale a [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install) e execute `databricks auth login --host https://SEU-WORKSPACE --profile fast-track`, substituindo o endereço pelo do seu workspace. Autorize no navegador; não coloque tokens no projeto. O perfil precisa poder usar o warehouse, catálogo e schema, e consultar as views. Para usar outro perfil, defina `DATABRICKS_CONFIG_PROFILE`. O comando seleciona automaticamente o único warehouse disponível; havendo vários, escolha um ID com `databricks warehouses list --profile fast-track` e defina `DATABRICKS_WAREHOUSE_ID`.

## Como organizei

```text
src/
  config.py       período e limites da coleta
  http_client.py  chamadas HTTP, intervalo e novas tentativas
  extract.py      coleta e manifesto dos arquivos brutos
  transform.py    carrega os JSONs e executa o SQL
  quality.py      verificações e avisos de qualidade
  persist.py      grava e relê os Parquets
  pipeline.py     liga as etapas e recebe os argumentos
  consultar_views.py  consulta opcional das views publicadas no Databricks
sql/
  transform.sql   desaninhamento, JOIN e indicadores
docs/apis/        chamadas das APIs, exemplos JSON e regras do cruzamento
tests/            testes com dados pequenos e respostas simuladas
output/
  latest.json     aponta para a última entrega aprovada
  runs/<id>/      relatório e tabelas particionadas por ano
```

Separei os arquivos por responsabilidade para conseguir corrigir uma etapa sem mexer no fluxo todo. Não usei camadas ou ferramentas extras que não eram necessárias para executar o desafio.

## O que acontece no tratamento

1. Converto ano, data, citações e acesso aberto para os tipos usados na análise. Uma data inválida fica nula e reprova a validação.
2. Mantenho citações e acesso aberto desconhecidos como nulos. Tema ausente recebe `Não informado`. Não trato dado ausente como zero.
3. Removo trabalhos repetidos pelo ID. Também removo afiliações repetidas do mesmo trabalho, comuns quando há vários autores na mesma instituição.
4. Uso `json_each` no SQL para abrir as listas de autores e instituições. Depois mantenho as instituições brasileiras.
5. Cruzo cidade e UF com o IBGE. Padronizo caixa e acentos e trato `Federal District` como `Distrito Federal`. Não faço aproximação por semelhança de nome.
6. Calculo contagens por ano, instituição, localidade e tema principal, além de participação geográfica, acesso aberto, citações e variação anual.

O total nacional vem de `meta.count` da API. Para citações e acesso aberto do recorte, uso `works`, com trabalhos distintos. Os indicadores por instituição e localidade contam trabalhos distintos em cada grupo. Assim, as várias afiliações não multiplicam as métricas de um mesmo trabalho.

Um trabalho pode aparecer em mais de uma cidade ou estado. Por isso, as participações geográficas podem somar mais de 100%. A localização é da instituição cadastrada, não necessariamente do campus de cada autor. Uso o tema principal do trabalho, sem abrir todos os temas em múltiplas contagens.

## Qualidade e saída

A auditoria verifica tipos, campos obrigatórios, proporção de nulos por coluna, chaves únicas, datas, intervalos e contagens antes e depois dos cruzamentos. Ela também confere a cobertura informada pela fonte.

Erros de estrutura ou consistência bloqueiam a gravação dos Parquets. Coleta parcial e campos opcionais ausentes ficam como avisos. O relatório inclui as instituições sem município e os dados da coleta, com data, cobertura e hashes.

| Pasta na execução | Conteúdo | Uma linha representa |
|---|---|---|
| `production/` | Base tratada com afiliações e geografia | Trabalho + instituição brasileira |
| `annual/` | Totais, cobertura, variação, acesso aberto e citações | Ano |
| `institution_annual/` | Trabalhos distintos por instituição | Ano + instituição |
| `geography/` | Contagem e participação por município, UF e região | Ano + nível + localidade |
| `topics/` | Contagem por tema principal | Ano + tema |

Todos os Parquets usam Snappy e pastas `year=2023`, por exemplo. `quality_report.json` fica na mesma execução. O pipeline relê os arquivos para conferir a quantidade de linhas e a compressão. Só depois atualiza `output/latest.json`.

Em `annual`, `source_available_works` é o total do filtro da API e `national_growth_rate` é sua variação anual. `works_count`, `oa_share`, `citations` e `sample_growth_rate` vêm do recorte. `collection_coverage` mostra a fração coletada. Cobertura e proporções ficam entre 0 e 1. Já `national_growth_rate` e `sample_growth_rate` podem ser negativas ou maiores que 1. Multiplique por 100 para mostrar em porcentagem: por exemplo, `-0.04` significa queda de 4%. Em acesso aberto, o denominador usa os trabalhos com esse campo conhecido (`oa_known`).

## Testes

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Os testes não chamam as APIs. Eles cobrem paginação, limite de requisições, falhas de rede, autores truncados, duplicatas, cidades homônimas, tradução do DF, nulos, datas inválidas, hashes e gravação dos Parquets. Há também um caso que diferencia crescimento nacional de tamanho da página coletada.

Os problemas encontrados durante a implementação estão em [APRENDIZADOS.md](APRENDIZADOS.md).

## Conferência antes da entrega

Na revisão de 23/11/2026, rodei os 17 testes novamente e todos passaram. Também baixei uma cópia pública do repositório, instalei as dependências e executei `run.sh` com as duas APIs reais. O fluxo terminou com a auditoria aprovada e gerou os 15 Parquets com Snappy e partição por ano.

Na consulta de hoje, os 300 trabalhos geraram 595 pares de trabalho e instituição. A coleta entregue, feita em 22/11, tem 591 pares. Mantive os arquivos de 22/11 em `output/`, porque são eles que sustentam os números de `RESULTADOS.md` e da apresentação. Fiz o teste de hoje em outra pasta para não misturar as duas execuções.

Essa diferença reforça o cuidado com a origem dos dados: as fontes podem mudar entre consultas. Para conferir os números apresentados, use os Parquets indicados em `output/latest.json`. Uma nova execução testa o fluxo com os dados disponíveis naquele momento e pode trazer outros resultados. O aviso de coleta parcial continua esperado pelo limite de uma página por ano.

## Se der problema

- Erro 401 ou 403: confira a chave e as regras de acesso do OpenAlex.
- Erro 429 ou 5xx: o cliente tenta de novo, com espera crescente e respeito ao `Retry-After`. Depois de quatro tentativas, para.
- Falha de conexão: confira a rede. Há timeout de conexão e leitura.
- Qualidade reprovada: veja os checks em `quality_report.json`. Não há Parquet novo nessa execução.
- Outras falhas: veja `failure.json` na pasta da execução. A mensagem guarda a classe do erro, sem copiar URLs que poderiam conter credenciais.

O programa retorna código diferente de zero em caso de falha. A última entrega aprovada continua disponível.

## Onde cada requisito foi atendido

| Requisito | Onde conferir |
|---|---|
| Duas APIs de domínios diferentes | `src/extract.py` |
| Limite de taxa, retentativas e credenciais no ambiente | `src/http_client.py` e `src/config.py` |
| Código modular e type hints | `src/` |
| Desaninhamento SQL e cinco ou mais transformações | `sql/transform.sql` |
| Schema, nulos, unicidade e intervalos | `src/quality.py` |
| Relatório JSON | `output/runs/<id>/quality_report.json` |
| Parquet, Snappy e partição temporal | `src/persist.py` e `output/` |
| Execução ponta a ponta | `./run.sh` |
| Dependências fixadas | `requirements.txt` |

A [especificação original](desafio/FT03_Engenharia_PRJ01_Python.pdf) está em `desafio/`. O envio do link pelo formulário da atividade continua sendo uma etapa fora do pipeline.
