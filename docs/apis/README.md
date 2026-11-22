# APIs, cruzamento dos dados e escolha dos Parquets

Este README explica o que foi usado das APIs, como repetir uma chamada e como os dados chegam às tabelas finais. Voltar ao [README principal](../../README.md) ou ao [guia do código](../../GUIA_PASSO_A_PASSO.md).

As consultas e a documentação oficial foram conferidas em **22/11/2026**. As APIs podem mudar depois dessa data. Os exemplos JSON abaixo mostram só os campos de interesse, não toda a resposta de cada serviço.

## 1. O papel de cada fonte

| Fonte | Pergunta que ajuda a responder | O que não fornece para este projeto |
|---|---|---|
| OpenAlex | Quais trabalhos estão ligados a instituições brasileiras, em qual ano e com quais afiliações? | Código oficial de município do IBGE |
| IBGE Localidades | A qual município, UF e região pertence um nome de localidade? | Trabalhos científicos, citações ou autores |

A ligação entre as duas fontes passa pela localização da instituição. Não existe uma chave de município do IBGE pronta dentro da resposta do OpenAlex. Essa diferença explica por que o cruzamento precisa de normalização e conferência.

## 2. Antes das chamadas: HTTP e JSON

O método usado é **GET**: o programa pede dados e não altera registros nas APIs. Os filtros vão como parâmetros da URL. No código, uso `params={...}` do requests para ele montar a URL e codificar caracteres como `:`, `|` e `*`.

O formato esperado é **JSON**. Um objeto usa chaves `{}`, uma lista usa colchetes `[]`, textos usam aspas, números não usam aspas e um valor desconhecido pode vir como `null`. O Python transforma isso em `dict`, `list`, `str`, números e `None` quando chama `response.json()`.

Essa estrutura importa porque um trabalho não vem como uma linha simples de planilha: ele pode ter vários autores, e cada autor pode ter várias instituições.

## 3. OpenAlex: acesso e limites

- URL base: `https://api.openalex.org`.
- Autenticação usada no projeto: parâmetro `api_key`, lido de `OPENALEX_API_KEY` no ambiente.
- Sem chave, a consulta pequena funcionou, mas usa o orçamento compartilhado do IP.
- Para seguir o cursor depois da primeira página, é preciso chave verificada.
- O programa mantém pelo menos um segundo entre chamadas por padrão. Não tenta usar toda a capacidade do serviço.

A chave pode ser obtida nas configurações da sua conta OpenAlex. O projeto não cria contas, não solicita chaves por e-mail e não guarda credenciais nos JSONs. O `.env` está ignorado pelo Git, mas não é carregado automaticamente pelo programa.

A documentação atual informa até cem resultados por página como limite suportado. Duzentos ainda podem funcionar por compatibilidade antiga, mas esse uso foi descontinuado. Na revisão, ajustei a consulta de instituições para cinquenta, o mesmo tamanho do lote de IDs. A chamada real retornou as cinquenta instituições esperadas.

Referências: [autenticação e limites](https://help.openalex.org/api/authentication/) e [paginação](https://help.openalex.org/api/paging/). Para consumo maior, confira as regras de orçamento da sua conta antes de aumentar a coleta.

## 4. Buscar trabalhos: `GET /works`

A implementação está em [`collect`, em src/extract.py](../../src/extract.py).

### Parâmetros usados

| Parâmetro | Exemplo | Motivo |
|---|---|---|
| `filter` | `institutions.country_code:br,publication_year:2023` | Exige afiliação brasileira e seleciona o ano |
| `sort` | `publication_date:asc` | Ordena por data crescente; a ordem foi aceita na consulta real |
| `per_page` | `100` | Controla o tamanho da página; no código aceita de um a cem |
| `cursor` | `*` na primeira chamada | Permite seguir as próximas páginas com `next_cursor` |
| `select` | `id,display_name,publication_year,publication_date,cited_by_count,open_access,primary_topic,authorships` | Reduz os campos baixados aos que o projeto usa |
| `api_key` | Valor da variável de ambiente, quando presente | Usa a autenticação da conta sem fixar a chave no código |

A vírgula no filtro combina condições: país **e** ano. O país é o da instituição associada ao trabalho; isso não identifica a nacionalidade de cada autor. O filtro também não limita o tipo a artigo de periódico: o recorte pode incluir outros tipos de trabalho indexados.

### Exemplo no terminal

O exemplo usa dois registros para facilitar a inspeção. Não precisa ser executado para usar `run.sh`.

```bash
curl --get 'https://api.openalex.org/works' \
  --data-urlencode 'filter=institutions.country_code:br,publication_year:2023' \
  --data-urlencode 'sort=publication_date:asc' \
  --data-urlencode 'per_page=2' \
  --data-urlencode 'cursor=*' \
  --data-urlencode 'select=id,display_name,publication_year,publication_date,cited_by_count,open_access,primary_topic,authorships'
```

Para uma chamada com chave, o código Python lê o ambiente e acrescenta o parâmetro. Evite colar uma URL com a chave em documentos, tickets ou prints.

### Exemplo curto em Python

```python
import os
from src.http_client import HttpClient

params = {
    'filter': 'institutions.country_code:br,publication_year:2023',
    'sort': 'publication_date:asc',
    'per_page': 2,
    'cursor': '*',
    'select': 'id,display_name,publication_year,publication_date,cited_by_count,open_access,primary_topic,authorships',
}
key = os.getenv('OPENALEX_API_KEY')
if key:
    params['api_key'] = key

page = HttpClient(interval=1).get('https://api.openalex.org/works', params)
print(page['meta']['count'])
print(len(page['results']))
```

`meta.count` informa o tamanho do filtro. `len(results)` informa o tamanho da página recebida. Na entrega, esses valores foram bem diferentes: por exemplo, a API informou 297.433 trabalhos para 2023, mas foram baixados cem.

### Formato esperado da resposta

Este exemplo é didático: `W_EXEMPLO`, `I_EXEMPLO` e o título não são um registro real. O número três também é ilustrativo.

```json
{
  "meta": {
    "count": 3,
    "per_page": 1,
    "next_cursor": "cursor-da-proxima-pagina"
  },
  "results": [
    {
      "id": "https://openalex.org/W_EXEMPLO",
      "display_name": "Trabalho de exemplo",
      "publication_year": 2023,
      "publication_date": "2023-01-02",
      "cited_by_count": 10,
      "open_access": {"is_oa": true},
      "primary_topic": null,
      "authorships": [
        {
          "institutions": [
            {
              "id": "https://openalex.org/I_EXEMPLO",
              "display_name": "Instituição de exemplo",
              "country_code": "BR"
            }
          ]
        }
      ]
    }
  ]
}
```

### Campos que o projeto espera

| Caminho JSON | Tipo esperado na fonte | Uso no projeto |
|---|---|---|
| `meta.count` | Inteiro | Total do filtro por ano, cobertura e evolução nacional |
| `meta.next_cursor` | Texto ou nulo | Próxima página; o código trata a ausência como fim |
| `results` | Lista de objetos | Trabalhos recebidos |
| `results[].id` | Texto | Chave do trabalho e remoção de duplicatas |
| `results[].display_name` | Texto ou nulo | Título; vazio vira nulo |
| `results[].publication_year` | Inteiro | Ano da análise e da partição |
| `results[].publication_date` | Texto no formato `YYYY-MM-DD` | Conversão para data e conferência com o ano |
| `results[].cited_by_count` | Inteiro; ausências são medidas | Citações do recorte |
| `results[].open_access` | Objeto ou nulo | Contém o indicador de acesso aberto |
| `results[].open_access.is_oa` | Booleano ou nulo | Proporção e quantidade em acesso aberto |
| `results[].primary_topic` | Objeto ou nulo | Tema principal, sem abrir múltiplos temas por trabalho |
| `results[].primary_topic.id, display_name` | Textos quando o tema existe | Identificação e nome do tema |
| `results[].authorships` | Lista de objetos | Autores e suas afiliações |
| `authorships[].institutions` | Lista de objetos | Instituições associadas ao autor |
| `authorships[].institutions[].id, display_name` | Textos | Chave e nome da instituição |
| `authorships[].institutions[].country_code` | Texto | Mantém instituições brasileiras no desaninhamento |

O schema de leitura está em [`src/transform.py`](../../src/transform.py). Ele lê os objetos aninhados como JSON, e o SQL faz as conversões. Campo opcional ausente pode continuar nulo; campo obrigatório inválido ou fora do período é barrado na auditoria.

Dicionários oficiais: [trabalhos](https://help.openalex.org/data/works/attributes/) e [autorias](https://help.openalex.org/data/authorships/).

## 5. Paginação e autores completos

### Como o código muda de página

1. Começa o ano com `cursor='*'`.
2. Faz a chamada e acrescenta `results` à lista coletada.
3. Guarda o total de `meta.count` e soma quantos registros chegaram.
4. Troca o cursor pelo valor de `meta.next_cursor`.
5. Para quando termina a resposta, chega ao total informado ou atinge `--max-pages`.
6. Registra se o ano ficou completo ou parcial no manifesto.

Se o limite for uma página e houver mais trabalhos disponíveis, o programa termina com uma coleta parcial registrada. Ele não finge que baixou o restante. A paginação não é uma fotografia imutável: a fonte pode mudar durante a coleta.

### Por que existe `GET /works/{id}`?

A listagem mostra no máximo cem autores por trabalho. Uma afiliação brasileira pode estar depois desse limite. Quando a lista chega a cem autores, o código consulta o registro individual e substitui `authorships` antes de levantar as instituições.

Exemplo de endpoint real:

```bash
curl 'https://api.openalex.org/works/W4313488537'
```

Essa resposta é **um objeto de trabalho**, sem a lista `results` e sem o bloco `meta` da paginação. O código usa o campo `authorships` desse objeto. O endpoint individual também tem um limite de milhares de autores; não é uma garantia de detalhe infinito.

Na entrega, nove trabalhos passaram por essa consulta. A regra surgiu depois que a auditoria encontrou três trabalhos sem afiliação brasileira visível na listagem. Veja [o registro do problema](../../APRENDIZADOS.md).

## 6. Buscar instituições: `GET /institutions`

A afiliação dentro do trabalho tem ID e nome, mas não traz o objeto `geo` completo de que precisamos. Por isso existe uma segunda consulta ao OpenAlex.

O programa junta os IDs brasileiros em um conjunto, remove repetidos, ordena e faz lotes de até cinquenta. O filtro une os IDs com `|`, que significa **ou** nesse caso.

```bash
curl --get 'https://api.openalex.org/institutions' \
  --data-urlencode 'filter=openalex_id:I17974374|I181391015' \
  --data-urlencode 'per_page=50' \
  --data-urlencode 'select=id,display_name,country_code,geo'
```

Os IDs acima são exemplos reais de USP e Unicamp. A consulta usa o mesmo cliente, intervalo e autenticação da coleta de trabalhos. A resposta da listagem tem `meta` e `results`.

Trecho reduzido de uma instituição que apareceu na coleta:

```json
{
  "id": "https://openalex.org/I17974374",
  "display_name": "Universidade de São Paulo",
  "country_code": "BR",
  "geo": {
    "city": "São Paulo",
    "region": "São Paulo",
    "country_code": "BR"
  }
}
```

| Campo | Tipo esperado | Por que é usado |
|---|---|---|
| `id` | Texto | Liga o detalhe à afiliação do trabalho |
| `display_name` | Texto | Nome da instituição |
| `country_code` | Texto | Confirma o país da instituição |
| `geo` | Objeto ou nulo | Localização cadastrada |
| `geo.city` | Texto ou nulo | Nome da cidade para o JOIN |
| `geo.region` | Texto ou nulo | Nome da UF/região administrativa; no Brasil, usamos para encontrar a UF |

O objeto `geo` pode ter latitude, longitude e identificador GeoNames, mas o projeto não usa esses campos para adivinhar município. O código do GeoNames não é o código do IBGE. A localização cadastrada também não comprova o campus de cada autor.

Referência: [instituições e seus campos](https://help.openalex.org/data/institutions/).

## 7. IBGE: `GET /api/v1/localidades/municipios`

- Serviço: API de Localidades do IBGE.
- Endpoint completo: `https://servicodados.ibge.gov.br/api/v1/localidades/municipios`.
- Acesso utilizado: GET, sem chave e sem parâmetros.
- Resposta esperada: uma **lista JSON de municípios**, sem `meta` e sem `results`.
- O pipeline recebe a lista inteira nessa chamada; não implementa paginação para esse endpoint.

```bash
curl 'https://servicodados.ibge.gov.br/api/v1/localidades/municipios'
```

No Python do projeto, a chamada é:

```python
municipalities = client.get(IBGE)
```

`client` é a mesma instância de `HttpClient` da coleta. Assim o IBGE recebe o mesmo cuidado com intervalo, timeout e falhas transitórias.

Abaixo está um recorte da resposta de São Paulo, com os campos usados pelo código. A API também devolve outros campos, como a divisão por microrregião, que não entram neste cruzamento.

```json
[
  {
    "id": 3550308,
    "nome": "São Paulo",
    "regiao-imediata": {
      "regiao-intermediaria": {
        "UF": {
          "sigla": "SP",
          "nome": "São Paulo",
          "regiao": {"nome": "Sudeste"}
        }
      }
    }
  }
]
```

| Caminho JSON | Tipo esperado | Coluna tratada |
|---|---|---|
| `[].id` | Inteiro | `municipality_id` |
| `[].nome` | Texto | `municipality` |
| `[].regiao-imediata.regiao-intermediaria.UF.sigla` | Texto | `state_code` |
| `[].regiao-imediata.regiao-intermediaria.UF.nome` | Texto | `state` |
| `[].regiao-imediata.regiao-intermediaria.UF.regiao.nome` | Texto | `region` |

Os nomes com hífen precisam ser tratados como nomes de chave, não como subtração. No SQL, uso aspas no caminho JSON, por exemplo `$."regiao-intermediaria".UF.sigla`.

Documentação: [IBGE Localidades](https://servicodados.ibge.gov.br/api/docs/localidades). Para este projeto, não foi assumido um limite numérico oficial de chamadas do IBGE; o cliente já usa uma espera conservadora.

## 8. Como as fontes são cruzadas, passo a passo

O SQL completo está em [`sql/transform.sql`](../../sql/transform.sql).

### Passo 1: abrir autores e instituições

```sql
FROM works w,
     LATERAL json_each(w.authorships) a,
     LATERAL json_each(a.value, '$.institutions') i
WHERE json_extract_string(i.value, '$.country_code') = 'BR'
```

O primeiro `json_each` abre autores. O segundo abre as instituições de cada autor. O `WHERE` mantém somente as brasileiras. O `SELECT DISTINCT` da consulta completa remove pares repetidos de trabalho e instituição.

### Passo 2: ligar a afiliação ao detalhe da instituição

A chave aqui é o ID do OpenAlex: `institution_id`. Esse é um cruzamento por identificador, sem comparar nomes de universidades. O detalhe da instituição fornece `geo.city` e `geo.region`.

### Passo 3: preparar nomes para o cruzamento geográfico

A macro `normalizar` aplica `trim`, `strip_accents` e `lower`. Assim, por exemplo, `São Paulo` e `sao paulo` ficam comparáveis. Ela não corrige erros de digitação nem faz busca por nome parecido.

Há uma regra explícita: `Federal District` vira `Distrito Federal` para comparar a UF. Esse foi um caso real encontrado na auditoria, não uma tradução automática de qualquer texto.

### Passo 4: comparar cidade e UF com o IBGE

O JOIN exige:

- cidade normalizada do OpenAlex igual ao município normalizado do IBGE;
- UF normalizada do OpenAlex igual ao nome ou à sigla da UF do IBGE, depois do tratamento do DF.

Só comparar cidade seria arriscado porque municípios de UFs diferentes podem ter o mesmo nome. Não uso o nome da instituição como cidade e não uso coordenadas para escolher o município mais próximo.

### Passo 5: preservar falhas e acrescentar os códigos

O cruzamento geográfico usa `LEFT JOIN`. Se não houver correspondência, a afiliação permanece e as colunas do IBGE ficam nulas. `geo_status` registra o motivo, e a auditoria lista as instituições afetadas.

Quando encontra o município, o código acrescenta ID oficial, nome, sigla e nome da UF e região brasileira. Na entrega, os 591 pares encontraram município: 567 sem tradução de UF e 24 com a regra do Distrito Federal.

### Passo 6: contar na unidade correta

- Nacional: usa `meta.count` do filtro por ano.
- Trabalhos coletados: uma linha por `work_id` em `works`.
- Instituições: um trabalho conta uma vez por instituição.
- Geografia: um trabalho conta uma vez por localidade em cada nível.
- Temas: usa só o tema principal de cada trabalho.

Por isso, a soma por localidades ou instituições pode ultrapassar o total de trabalhos. A participação geográfica divide pelo recorte coletado, não pelo total nacional da API.

## 9. Respostas inesperadas e qualidade

| Situação | O que o programa faz |
|---|---|
| Timeout ou erro de conexão | Tenta de novo dentro do limite configurado |
| HTTP 429 ou 5xx | Espera e tenta novamente; usa `Retry-After` quando ele vem válido |
| HTTP 400, 401 ou 403 | Para, pois repetir o mesmo parâmetro ou a mesma chave não resolve o problema |
| Corpo que não é JSON | Retorna erro sem copiar o conteúdo externo para o log |
| Trabalhos sem lista `results` ou sem `meta.count` | Recusa a resposta fora do formato esperado |
| Lista de municípios vazia ou com outro formato | Interrompe a coleta |
| Datas inválidas, chaves nulas ou duplicadas | A auditoria reprova a entrega antes de gravar Parquet |
| Município não encontrado | Preserva a linha, registra nulo e gera aviso e lista de pendências |
| Limite de páginas atingido | Marca coleta parcial; não considera isso cobertura completa |

O programa salva os JSONs em `data/raw/<id>/`: `works.json`, `institutions.json`, `municipalities.json` e `manifest.json`. O manifesto guarda fontes, período, forma de seleção, cobertura e hashes. A chave não é copiada para ele.

Antes do tratamento, os hashes dos três arquivos são recalculados. Depois do SQL, a auditoria confere as tabelas. Após a gravação, o programa relê os Parquets para conferir contagens e compressão.

## 10. Parquet: o que o desafio pediu e o que foi escolha do projeto

### O que veio do enunciado

O desafio pede os dados finais em **Parquet ou Delta Lake**, com **Snappy**, organizados com uma **partição temporal**. Também pede um **relatório de qualidade JSON ou CSV**.

Escolhi Parquet e partição por ano. Para este volume e essa pergunta, é mais simples trabalhar com ano de publicação do que criar pastas por mês. A base final principal é `production`: um par de trabalho e instituição por linha.

### O que foi uma escolha da implementação

O enunciado **não pede especificamente Parquets de indicadores** nem obriga criar as tabelas `annual`, `institution_annual`, `geography` e `topics`. Essas tabelas foram uma escolha para deixar os cálculos prontos para consulta, com as regras de contagem definidas em SQL.

| Tabela | Por que foi salva |
|---|---|
| `production` | Entrega a base tratada e cruzada, pedida como dataset final |
| `annual` | Separa total nacional, cobertura e métricas dos trabalhos coletados |
| `institution_annual` | Evita refazer a contagem distinta por instituição em cada consulta |
| `geography` | Guarda municípios, UFs, regiões e suas participações com a mesma regra de cálculo |
| `topics` | Facilita consultar o tema principal por ano e acesso aberto |

Salvar os indicadores no mesmo formato foi uma conveniência, não uma regra extra atribuída ao desafio. O relatório de qualidade continua em JSON, como permitido no enunciado.

### Por que esse formato ajuda aqui?

Parquet guarda dados por colunas e preserva tipos. Isso combina com consultas que leem só algumas colunas, como ano e contagem. Snappy comprime os arquivos. A pasta `year=2023` permite localizar um período sem misturar tudo em um único arquivo.

Não foi feito um benchmark para afirmar que Parquet é mais rápido neste recorte de 300 trabalhos. A escolha atende ao enunciado e mantém um formato útil caso o conjunto cresça. O DuckDB já grava e lê esse formato, então não foi necessário instalar outra biblioteca só para isso.

## 11. Conferências feitas

- Consultas reais das duas APIs, usando os mesmos endpoints do código.
- Consulta individual dos trabalhos com lista longa de autores.
- Consulta de cinquenta instituições com `per_page=50`, conferindo os cinquenta IDs retornados.
- Testes simulados de paginação, erros HTTP e autores truncados.
- Testes de cidades homônimas, DF, nulos, datas, duplicatas e leitura do Parquet.
- Execução ponta a ponta e auditoria do recorte final.

Para ler o código por linhas e entender o restante do fluxo, siga o [guia passo a passo](../../GUIA_PASSO_A_PASSO.md). Para ver os números e os limites da interpretação, consulte [RESULTADOS.md](../../RESULTADOS.md).
