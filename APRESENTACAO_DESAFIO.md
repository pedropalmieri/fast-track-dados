# Como resolvi o desafio de dados com Python e SQL

Desenvolvi este projeto como prática após a **Trilha Engenharia de Dados POD TILLER**, disponibilizada pela Compass UOL na Udemy. Minha ideia foi aplicar os estudos em uma atividade que passasse por coleta, tratamento, cruzamento, qualidade e entrega dos dados.

Neste documento eu conto o caminho que segui, os arquivos que criei, os problemas que encontrei e o que consegui obter. O código está organizado em [`src/`](src/), as consultas estão em [`sql/transform.sql`](sql/transform.sql) e os resultados estão em [`output/`](output/).

## Primeiro, entendi o que eu precisava entregar

Comecei pelo enunciado do desafio. Separei os pedidos principais: consumir pelo menos duas APIs de domínios diferentes, usar Python com funções organizadas e trabalhar com SQL para abrir estruturas aninhadas.

Também identifiquei os tratamentos obrigatórios: converter tipos e datas, lidar com nulos, remover duplicatas, cruzar fontes e acrescentar métricas. Depois disso, eu precisava conferir a qualidade e salvar os dados em Parquet ou Delta Lake, com Snappy e partição temporal. O relatório de qualidade poderia ser JSON ou CSV.

Usei esses pontos para orientar a implementação. No fim do [README principal](README.md), deixei uma tabela mostrando onde cada requisito foi atendido. Assim fica mais fácil conferir a entrega sem precisar procurar tudo pelo código.

## Depois, defini a pergunta e mantive a ideia inicial

Parti da ideia que já estava no começo do repositório: estudar a produção científica ligada a instituições brasileiras usando OpenAlex e IBGE.

Eu queria observar como a contagem de trabalhos muda por ano e como os trabalhos se distribuem entre instituições, municípios, estados, regiões e temas. Antes de seguir, conferi se essa combinação realmente ajudava no desafio.

O OpenAlex tem os trabalhos, os autores e suas instituições. O IBGE tem os códigos oficiais de município e a hierarquia de estados e regiões. Essa combinação permitiu cruzar duas fontes de assuntos diferentes e trabalhar com listas dentro de JSON, que eu precisaria abrir com SQL.

Também defini um limite para a interpretação. Com essas fontes eu consigo estudar a produção indexada e as afiliações. Eu não consigo explicar o efeito de financiamento ou incentivos à pesquisa, porque não incluí uma fonte com esse tipo de informação.

## Escolhi um período e comecei com uma coleta pequena

Para a entrega, usei 2023, 2024 e 2025. Escolhi anos encerrados para evitar comparar um ano em andamento com anos completos. Mesmo assim, a base pode continuar recebendo registros e correções desses períodos.

Comecei com uma página de cem trabalhos por ano, ordenada por data de publicação crescente. Isso deixou a execução menor para testar o fluxo com dados reais. Ao mesmo tempo, eu precisava registrar que esse recorte não é aleatório e não representa todos os trabalhos do Brasil.

Coloquei os parâmetros em [`src/config.py`](src/config.py). Nesse arquivo defini os anos, o limite de páginas, a quantidade por página e o intervalo entre chamadas. Também fiz validações para recusar período inválido, tamanho de página fora do limite e mais de uma página sem chave do OpenAlex.

Por padrão, o programa usa os três anos anteriores ao ano atual. Os anos da entrega também podem ser informados no comando, para repetir o mesmo período.

## Preparei o ambiente antes de montar as etapas

Criei um ambiente virtual para separar as bibliotecas do projeto das usadas em outros trabalhos. Registrei as versões em [`requirements.txt`](requirements.txt).

Usei `requests` para as chamadas HTTP e DuckDB para ler JSON, executar SQL e gravar Parquet. Escolhi DuckDB porque ele roda junto com o Python, sem precisar montar um serviço de banco separado. Para o volume desta atividade, isso foi suficiente.

Também criei [`.gitignore`](.gitignore) para deixar fora do Git o ambiente virtual, arquivos gerados pelo Python, JSONs brutos e arquivos locais de credenciais. A chave do OpenAlex é lida do ambiente; não foi colocada no código.

## Centralizei as chamadas para não repetir o tratamento de rede

Antes de buscar os dados, criei [`src/http_client.py`](src/http_client.py). Minha intenção foi usar o mesmo cuidado nas chamadas das duas fontes, em vez de repetir regras em cada consulta.

Nesse cliente eu coloquei intervalo mínimo entre chamadas, timeout de conexão e leitura e limite de tentativas. Quando acontece timeout, falha de conexão, HTTP 429 ou erro de servidor, ele pode tentar novamente com espera crescente.

Também tratei o cabeçalho `Retry-After`, quando a API informa quanto tempo precisa esperar. Para erros como parâmetro inválido ou chave recusada, o cliente para, porque repetir o mesmo pedido não resolveria o problema.

Eu limitei as tentativas para evitar que o programa ficasse tentando sem parar. As mensagens também não copiam a URL autenticada ou a resposta externa inteira, que poderiam conter dados desnecessários no log.

## Busquei os trabalhos na API do OpenAlex

Coloquei a coleta em [`src/extract.py`](src/extract.py). A primeira consulta vai para `https://api.openalex.org/works`.

Eu envio o filtro de instituição brasileira e ano de publicação. Também informo a ordenação por data, o tamanho da página, o cursor e os campos que serão usados. Um exemplo do filtro é:

```text
institutions.country_code:br,publication_year:2023
```

No código eu passo esses valores em um dicionário de parâmetros. O cliente HTTP monta a requisição. Quando existe `OPENALEX_API_KEY` no ambiente, ela é acrescentada à chamada.

A resposta vem em JSON. O bloco `meta` traz informações da consulta, como a contagem do filtro e o próximo cursor. A lista `results` traz os trabalhos da página. Dentro dos trabalhos ficam os autores e, dentro de cada autor, as instituições.

Eu selecionei ID, título, ano, data, citações, acesso aberto, tema principal e afiliações. Não precisei baixar todos os campos que o OpenAlex oferece.

## Fiz a paginação e guardei a cobertura da coleta

Para começar um ano, usei `cursor='*'`. Depois de cada resposta, acrescentei os trabalhos recebidos e li `meta.next_cursor` para saber qual seria a próxima página.

A coleta para quando termina a resposta ou chega ao limite de páginas escolhido. Se o limite for atingido antes de trazer todos os trabalhos, eu marco a coleta como parcial.

Guardei essas informações no manifesto da coleta: ano, total disponível, quantidade recebida e se a coleta ficou completa. Essa parte foi importante porque baixar cem trabalhos não significa que só existam cem trabalhos naquele ano.

Também registrei as fontes, o momento da coleta e os hashes SHA-256 dos arquivos. Os hashes permitem perceber se um JSON local mudou antes do reprocessamento. Eles não provam que a informação original da fonte está correta.

## Encontrei um erro de parâmetro na primeira tentativa

Na primeira versão, tentei ordenar os trabalhos por ID. A consulta real retornou HTTP 400, porque aquela ordenação não era aceita.

Troquei para `publication_date:asc`, testei novamente e registrei essa seleção no manifesto. Também considerei o efeito dessa escolha na análise: uma coleta limitada por data crescente pega primeiro o começo do ano e pode incluir datas preenchidas como primeiro de janeiro.

Eu deixei esse ajuste registrado em um commit separado e em [`APRENDIZADOS.md`](APRENDIZADOS.md). Foi um caso em que uma chamada pequena ajudou a corrigir o parâmetro antes de ampliar a coleta.

## Depois busquei o detalhe das instituições

A afiliação dentro do trabalho traz o ID e o nome da instituição, mas não a localização completa de que eu precisava. Por isso fiz outra consulta no OpenAlex, usando o endpoint de instituições.

Primeiro juntei os IDs brasileiros, removi repetidos e ordenei a lista. Depois separei os IDs em lotes de até cinquenta e usei um filtro que combina esses IDs com `|`, representando uma condição de um ID ou outro.

Essa parte também ficou em [`src/extract.py`](src/extract.py). Do detalhe, eu aproveitei principalmente `geo.city` e `geo.region`, que trazem cidade e estado/região administrativa cadastrados.

Na revisão da documentação das APIs, vi que pedir duzentos registros por página era um comportamento antigo, embora ainda tivesse funcionado. Como os lotes têm até cinquenta IDs, ajustei o pedido para cinquenta e conferi os cinquenta IDs de uma resposta real.

## Consumi a lista de municípios do IBGE

A segunda fonte foi `https://servicodados.ibge.gov.br/api/v1/localidades/municipios`. Fiz uma chamada GET sem chave, usando o mesmo cliente HTTP.

Diferente da resposta do OpenAlex, esse endpoint devolve uma lista JSON de municípios, sem os blocos `meta` e `results`. Cada município tem código, nome e informações de sua hierarquia geográfica.

Eu usei a ligação por região imediata e intermediária para extrair sigla e nome da UF e região brasileira. O código do município do IBGE não vinha pronto nos dados do OpenAlex; ele seria acrescentado no cruzamento.

Documentei as chamadas, os parâmetros, os exemplos de resposta e os tipos esperados em [`docs/apis/README.md`](docs/apis/README.md). Nesse arquivo também mostrei como consumir as APIs pelo terminal e pelo Python.

## Salvei os JSONs antes de transformar

Depois da coleta, salvei `works.json`, `institutions.json`, `municipalities.json` e `manifest.json` em uma pasta de `data/raw/` identificada pela execução.

Eu mantive esses arquivos separados dos resultados finais para conseguir reprocessar sem chamar as APIs outra vez. Os brutos ficam locais e não foram enviados ao repositório. Os Parquets finais e a auditoria foram incluídos na entrega.

Antes de usar os JSONs, o comando principal recalcula os hashes dos três arquivos de dados e compara com o manifesto. Se um deles estiver diferente, o reprocessamento para.

## Carreguei os dados no DuckDB e tratei os campos

Criei [`src/transform.py`](src/transform.py) para abrir o DuckDB em memória e carregar os três JSONs com os campos de entrada definidos. Depois fiz esse arquivo executar [`sql/transform.sql`](sql/transform.sql).

No SQL, comecei pelos trabalhos. Converti ano para inteiro, data para `DATE`, citações para inteiro e acesso aberto para booleano. Usei `try_cast` para que um valor que não pudesse ser convertido virasse nulo e pudesse ser identificado pela auditoria.

Para os nulos, mantive citações e acesso aberto desconhecidos sem preencher com zero. Zero significaria uma informação diferente. Para tema principal ausente, usei o nome `Não informado`, mantendo o ID do tema nulo.

Também removi trabalhos repetidos pelo ID do OpenAlex. A intenção foi ter uma tabela `works` com uma linha por trabalho antes de abrir as afiliações.

## Abri os autores e as instituições com SQL

Usei `json_each` duas vezes: uma para percorrer os autores do trabalho e outra para percorrer as instituições de cada autor. O trecho central ficou assim:

```sql
FROM works w,
     LATERAL json_each(w.authorships) a,
     LATERAL json_each(a.value, '$.institutions') i
WHERE json_extract_string(i.value, '$.country_code') = 'BR'
```

Depois usei `DISTINCT` no par de trabalho e instituição. Se dois autores do mesmo trabalho estão na mesma instituição, eu não quero contar aquele trabalho duas vezes para ela.

Essa etapa gerou a tabela `affiliations`. A partir dela, eu poderia ligar o trabalho aos detalhes de suas instituições sem depender da lista aninhada original.

## Cruzei os dados com o IBGE usando cidade e UF

Primeiro liguei a afiliação ao detalhe da instituição pelo ID do OpenAlex. Depois usei cidade e UF da instituição para encontrar o município no IBGE.

Criei uma normalização simples no SQL: tirar espaços nas pontas, remover acentos e colocar o texto em minúsculas. Isso ajuda a comparar formas como `São Paulo` e `sao paulo`, mas não tenta corrigir nomes por aproximação.

Eu exigi cidade e UF no JOIN. Só o nome da cidade poderia ligar um registro ao município errado, porque existem nomes iguais em estados diferentes. Para UF, aceitei o nome ou a sigla usada no cadastro do IBGE.

Usei `LEFT JOIN` para não apagar uma afiliação quando a localização não fosse encontrada. Nesses casos, os campos do IBGE ficam nulos e `geo_status` registra o que aconteceu. A auditoria também guarda uma lista das instituições sem município.

## A conferência mostrou um problema com o Distrito Federal

Ao revisar os registros sem correspondência, encontrei 24 pares ligados a Brasília. O OpenAlex usava `Federal District`, enquanto o IBGE usava `Distrito Federal`.

Adicionei uma regra explícita para essa tradução no JOIN. Também marquei esses casos como `correspondencia_uf_traduzida`, para que fosse possível separar o que precisou desse tratamento.

Depois do ajuste, os 591 pares da entrega receberam município, UF e região: 567 sem tradução de UF e 24 com a regra do DF. Eu considero isso uma correspondência dentro das regras implementadas. A localização continua sendo a da instituição cadastrada, não uma confirmação manual do campus de cada autor.

## A auditoria também encontrou autores incompletos

Durante as verificações, três trabalhos apareceram sem afiliação brasileira visível, apesar de terem sido retornados pelo filtro brasileiro. Fui conferir e encontrei uma limitação da listagem do OpenAlex: ela corta a lista em cem autores.

A instituição brasileira podia estar depois desse corte. Para resolver, voltei à coleta e acrescentei uma consulta ao endpoint individual quando a lista chegava a cem autores. Substituí `authorships` pela lista detalhada antes de buscar as instituições.

Nove trabalhos precisaram dessa consulta. Depois da correção, todos os trabalhos coletados tinham ao menos uma afiliação brasileira disponível. Mantive a verificação que encontrou o problema e acrescentei teste para essa situação.

## Separei os indicadores para não multiplicar as contagens

Depois do cruzamento, um trabalho pode estar em várias linhas, porque pode ter várias instituições. Por isso eu não calculei os totais de citações e acesso aberto somando diretamente a base de afiliações.

Usei a tabela `works`, com trabalhos distintos, para o resumo anual e os temas. Para instituição e geografia, contei trabalhos distintos em cada grupo. Assim um trabalho com duas instituições na mesma cidade conta uma vez naquela cidade.

Também considerei que um trabalho pode pertencer a cidades, estados ou regiões diferentes. Por isso as participações geográficas podem somar mais de 100%. Elas usam o total coletado no ano como denominador.

Salvei os indicadores em quatro tabelas: `annual`, `institution_annual`, `geography` e `topics`. A base tratada com as afiliações ficou em `production`.

## Diferenciei o total nacional do tamanho da página baixada

Como eu baixei cem trabalhos por ano, comparar só o tamanho da coleta daria crescimento de zero. Esse resultado seria consequência do meu limite, não uma conclusão sobre o país.

Aproveitei `meta.count`, informado pelo OpenAlex, para guardar o total do filtro brasileiro por ano. Acrescentei ao resumo anual `source_available_works`, `collection_coverage` e `national_growth_rate`.

Mantive `works_count`, `sample_growth_rate`, acesso aberto e citações ligados ao recorte. Também criei um teste com uma página do mesmo tamanho nos dois anos, mas totais nacionais diferentes, para conferir que os cálculos não fossem confundidos.

## Criei verificações antes de publicar os dados finais

Organizei a auditoria em [`src/quality.py`](src/quality.py). Comecei conferindo tipos de colunas, quantidade de linhas, chaves únicas e nulos nos campos obrigatórios. Também calculei a proporção de nulos por coluna.

Depois verifiquei datas, anos dentro do período, citações negativas e participações fora do intervalo esperado. Conferi se os trabalhos mantiveram afiliação brasileira e se os cruzamentos não perderam ou multiplicaram pares.

Separei os problemas em erros e avisos. Erro de estrutura ou consistência reprova a entrega. Coleta parcial e algumas informações opcionais ausentes ficam como avisos, sem serem escondidas.

Na execução entregue, foram 41 verificações: quarenta passaram e uma registrou o aviso esperado de coleta parcial. O relatório aprovado mostra que os dados passaram nessas regras. Ele não significa que o recorte seja representativo de todo o Brasil.

## Gravei a base e os indicadores em Parquet

Criei [`src/persist.py`](src/persist.py) para gravar a saída. Escolhi Parquet com Snappy e pastas por ano porque o desafio pedia Parquet ou Delta Lake, compressão Snappy e uma estratégia temporal de partição.

A base final principal é `production`, com uma linha por trabalho e instituição. Salvar também os quatro indicadores em Parquet foi uma escolha da implementação para deixar os cálculos prontos para consulta. O enunciado não exigia especificamente cada uma dessas tabelas de indicadores.

Depois de gravar, fiz o programa reler os arquivos e conferir quantidade de linhas e compressão. Só depois ele atualiza `output/latest.json`, que aponta para a última execução aprovada.

Cada execução usa uma pasta própria. Se uma exportação falhar, ela pode deixar arquivos parciais naquela pasta, mas não substitui o apontador da última entrega válida. O relatório de qualidade fica em JSON, junto dos dados.

## Liguei as etapas e deixei um comando para executar

Em [`src/pipeline.py`](src/pipeline.py), liguei coleta, conferência dos brutos, transformação, auditoria e gravação. Também acrescentei os argumentos do terminal e o fechamento da conexão no fim da execução.

Criei [`run.sh`](run.sh) para preparar o ambiente, instalar as dependências e chamar o pipeline. Para executar o período da entrega, o comando é:

```bash
./run.sh --start-year 2023 --end-year 2025 --max-pages 1 --per-page 100
```

Também deixei um modo de reprocessar uma pasta de brutos sem consultar as APIs:

```bash
.venv/bin/python -m src.pipeline --from-raw data/raw/ID_DA_COLETA
```

Nesse segundo caso, os metadados e os hashes daquela coleta orientam o processamento. Uma falha retorna código diferente de zero e gera um registro; o apontador só muda depois de uma entrega aprovada.

## Testei com exemplos pequenos e com dados reais

Separei os testes em [`tests/`](tests/). Usei exemplos pequenos para saber o que esperar de cada cálculo. Simulei chamadas HTTP para testar erros e paginação sem depender das APIs disponíveis naquele momento.

Cobri duplicatas, cidades homônimas, a tradução do DF, autores cortados, datas inválidas e valores desconhecidos. Também testei alteração de arquivo bruto, gravação e releitura dos Parquets e diferença entre crescimento nacional e tamanho do recorte.

Os 17 testes passaram. Além deles, executei o fluxo com as duas APIs reais. Depois baixei uma cópia limpa do repositório público e rodei os testes nela; os 17 também passaram sem depender dos brutos da pasta de desenvolvimento.

O comando dos testes ficou documentado no README:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Comparei o que eu esperava com o que obtive

Eu esperava entregar um fluxo que consumisse duas fontes, tratasse as listas do JSON com SQL, cruzasse a geografia e salvasse uma base conferida. Consegui executar essas etapas e gerar os arquivos finais.

A coleta feita em 22/11/2026 trouxe 300 trabalhos de 2023 a 2025, ligados a 209 instituições brasileiras. Depois do desaninhamento e da remoção de afiliações repetidas, obtive 591 pares de trabalho e instituição. Todos receberam município, UF e região pelas regras de correspondência utilizadas.

O OpenAlex informou os seguintes totais no filtro brasileiro:

| Ano | Total informado pela API | Variação em relação ao ano anterior |
|---|---:|---:|
| 2023 | 297.433 | - |
| 2024 | 309.317 | +4,00% |
| 2025 | 297.326 | -3,88% |

Eu observei uma contagem indexada maior em 2024 e menor em 2025. Não usei esses números para afirmar uma causa ou uma mudança de qualidade da pesquisa. A fonte pode ser atualizada e os trabalhos mais recentes ainda podem entrar depois.

Nos cem trabalhos coletados de cada ano, o acesso aberto ficou em 92%, 93% e 93%. As citações observadas foram 11.034, 10.848 e 6.585. Tratei citações com cuidado porque os trabalhos mais antigos tiveram mais tempo para recebê-las.

No recorte, a USP apareceu com 61 trabalhos e a Unicamp com dezoito. O Sudeste teve a maior contagem por região. Também apareceram temas ligados a educação e inteligência artificial. Esses resultados descrevem o recorte; eu não os apresentei como ranking nacional nem como prova dos temas mais pesquisados no país.

Deixei os números e os cuidados de interpretação em [`RESULTADOS.md`](RESULTADOS.md). A saída tem quinze arquivos Parquet, distribuídos entre cinco tabelas e três anos, e um relatório JSON.

## O que ficou de aprendizado e o que eu faria depois

A parte que mais exigiu conferência foi entender o que a resposta da API realmente trazia. Um filtro correto não garantia todos os autores visíveis. Uma cidade conhecida não garantia o mesmo nome de UF nas duas fontes. E uma coleta com a mesma quantidade por ano não servia para medir crescimento nacional.

As validações ajudaram a encontrar essas diferenças. Eu registrei os problemas e suas correções em commits separados e em [`APRENDIZADOS.md`](APRENDIZADOS.md), mantendo o motivo de cada ajuste.

Ainda há limites. A coleta representa cerca de 0,03% do total informado em cada ano e não é aleatória. O programa mantém os trabalhos em memória e ainda não retoma uma coleta interrompida do ponto em que parou. Para um volume muito maior, eu precisaria rever essa estratégia e planejar armazenamento, orçamento da API e retomada de falhas.

Como continuação, eu começaria pela cobertura antes de acrescentar mais ferramentas ou gráficos. Depois escolheria uma pergunta mais específica, como os temas de educação e IA, com uma coleta adequada para sustentá-la.

Ao final, consegui praticar o fluxo de engenharia de dados proposto no desafio: buscar, tratar, cruzar, conferir e disponibilizar. Usei a Trilha Engenharia de Dados POD TILLER como contexto de estudo e deixei as escolhas documentadas para conseguir repetir a execução e explicar o que cada etapa faz.
