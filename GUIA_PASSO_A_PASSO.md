# Guia do projeto, do começo até a saída

Este é o roteiro para ler, executar e explicar o desafio. O [README](README.md) é a entrada rápida. Aqui ficam o motivo das escolhas, o caminho dos dados e a leitura dos trechos do código.

Os números de linha abaixo se referem à versão entregue. Separei linhas que fazem parte da mesma operação na mesma explicação. Linhas em branco apenas separam os blocos; comentários e docstrings explicam a intenção. Se o código mudar, confira também essas referências.

## 1. Qual problema estamos tentando responder?

A pergunta inicial foi: como a produção científica ligada a instituições brasileiras muda por ano e se distribui entre instituições, localidades e temas?

Para não prometer mais do que os dados permitem, dividi a resposta:

1. A evolução nacional usa a contagem do filtro brasileiro informada pelo OpenAlex.
2. O detalhamento usa os trabalhos que foram realmente baixados. A entrega tem 100 por ano, de 2023 a 2025.

O resultado esperado é uma base que dê para consultar, com origem, regras de contagem e problemas conhecidos registrados. Não é uma avaliação da qualidade das universidades nem de políticas de financiamento.

## 2. Como saímos do PDF para a implementação

| Pedido do desafio | Decisão tomada | Por que fiz assim |
|---|---|---|
| Duas APIs de domínios diferentes | OpenAlex e IBGE | Uma traz pesquisa científica; a outra, geografia oficial |
| Python modular e type hints | Funções separadas em `src/` | Ajuda a ler, testar e corrigir uma etapa por vez |
| Desaninhar coleções em SQL | `json_each` no DuckDB | Os autores e as instituições vêm em listas dentro do JSON |
| Cinco transformações ou mais | Tipos, datas, nulos, duplicatas, JOIN e métricas | São tratamentos que os dados deste cenário realmente precisam |
| Resiliência | Intervalo, timeout e retentativas | A chamada pode falhar ou ser limitada pela API |
| Credenciais no ambiente | `OPENALEX_API_KEY` | A chave não precisa aparecer no código ou no Git |
| Qualidade automatizada | Regras de schema, nulos, chaves e intervalos | O programa precisa conferir o resultado, não só terminar sem erro |
| Formato colunar e partição temporal | Parquet com Snappy, separado por ano | Atende ao desafio e permite ler um período específico |
| Relatório | JSON junto da execução | Guarda os resultados das verificações e a cobertura |

Não foi preciso mudar o tema inicial do repositório. Ele já permitia trabalhar os pontos pedidos. Também não foi preciso usar Spark, servidor de banco ou agendador para esse volume.

## 3. Caminho de um trabalho dentro do pipeline

Imagine um trabalho W1 com dois autores na instituição I1 e outro autor na I2. As duas instituições são brasileiras.

1. O OpenAlex devolve W1 com os autores dentro de `authorships`.
2. Cada autor pode ter uma lista `institutions`.
3. O SQL abre primeiro os autores e depois as instituições.
4. O par W1-I1 aparece duas vezes, mas o `DISTINCT` deixa só uma.
5. O resultado tem dois pares: W1-I1 e W1-I2.
6. A contagem de trabalhos do ano continua sendo **um**. Ela vem da tabela `works`.
7. Se I1 e I2 estiverem na mesma cidade, a cidade conta W1 uma vez. Se estiverem em cidades diferentes, cada cidade conta W1 uma vez.

Por isso, não se deve somar a coluna de citações diretamente na base `production` para obter o total do ano: o trabalho pode estar em várias linhas. Use `annual` ou deduplique o trabalho antes da soma.

## 4. Preparar e executar

```bash
git clone https://github.com/pedropalmieri/fast-track-dados.git
cd fast-track-dados
./run.sh --start-year 2023 --end-year 2025 --max-pages 1 --per-page 100
```

O script instala as dependências em `.venv`. Para acompanhar o funcionamento sem aumentar a coleta, mantenha uma página por ano.

Se quiser mais páginas, configure sua chave no ambiente antes de rodar. Não coloque a chave na linha do código, em exemplos reais ou em capturas de tela. Os exemplos deste repositório usam apenas texto fictício.

```bash
export OPENALEX_API_KEY='sua-chave'
./run.sh --start-year 2023 --end-year 2025 --max-pages 5 --interval 1
```

Cinco páginas continuam sendo um limite de coleta, não uma garantia de cobertura total. O relatório informa quanto foi baixado e quanto a API dizia estar disponível.

### Argumentos do comando

| Argumento | O que controla | Padrão e cuidado |
|---|---|---|
| `--start-year` | Primeiro ano | Ano atual menos três |
| `--end-year` | Último ano | Ano anterior; não aceita o ano em andamento |
| `--max-pages` | Quantas páginas buscar por ano | Uma; mais de uma exige chave |
| `--per-page` | Trabalhos por página | Cem; aceita de um a cem |
| `--interval` | Espera mínima entre chamadas | Um segundo; não pode ser negativo |
| `--from-raw` | Pasta de uma coleta anterior | Não consulta as APIs; confere os hashes |
| `--output` | Pasta da entrega | `output/`; cada execução ganha outra subpasta |

Quando `--from-raw` é usado, período e cobertura vêm do manifesto daquela coleta. Os argumentos de coleta não refazem o filtro dos arquivos locais.

## 5. Ler os arquivos de apoio

### `run.sh`

| Linhas | O que fazem e por quê |
|---|---|
| 1-2 | Indicam Bash e explicam que o comando deve entrar na pasta do projeto |
| 3 | `set -euo pipefail` interrompe o script em falhas e uso de variável inexistente |
| 4-5 | `cd` usa a pasta do próprio script; isso evita procurar `requirements.txt` no lugar errado |
| 6-9 | Criam o ambiente virtual se ele ainda não existir. `PYTHON` permite escolher outro executável; o padrão é `python3` |
| 10 | Instala as versões listadas em `requirements.txt`; a opção de silêncio reduz mensagens de instalação |
| 11 | Troca o processo pelo comando Python e passa todos os argumentos com `"$@"`, preservando espaços |

### `requirements.txt`

| Biblioteca | Papel no projeto |
|---|---|
| `requests` | Faz chamadas HTTP e fornece as exceções de conexão e timeout |
| `duckdb` | Lê JSON, executa SQL, grava e inspeciona Parquet |
| `urllib3` | Dependência de transporte HTTP do requests |
| `certifi` | Certificados usados para verificar conexões HTTPS |
| `charset-normalizer` | Ajuda o requests a interpretar codificações de texto |
| `idna` | Trata nomes de domínio usados nas conexões |

As versões diretas e indiretas foram fixadas com `pip freeze` no ambiente do projeto. Isso ajuda a repetir o ambiente Python, mas não congela o conteúdo das APIs. O ambiente foi testado com Python 3.13; não há lock de sistema operacional ou imagem de contêiner.

### `.gitignore`

| Linha | Regra e motivo |
|---|---|
| 1 | `.venv/`: o ambiente é recriado, não enviado ao Git |
| 2-3 | `__pycache__/` e `*.pyc`: são arquivos gerados pelo Python |
| 4-5 | `.env` e `.env.*`: evitam versionar arquivos locais com credenciais |
| 6 | `data/`: os JSONs brutos ficam locais; os resultados finais ficam em `output/` |
| 7 | `.DS_Store`: arquivo de organização do macOS, sem utilidade para o projeto |

O `.gitignore` não remove um segredo que já tenha sido versionado. Por isso a chave é lida do ambiente desde a coleta.

## 6. Configurações: `src/config.py`

| Linhas | Leitura do trecho |
|---|---|
| 1-7 | A docstring apresenta o arquivo. `os` lê o ambiente; `dataclass` monta a configuração; `date` ajuda a escolher anos encerrados |
| 8-9 | `@dataclass(frozen=True)` cria uma configuração que não pode ser alterada depois de instanciada |
| 10 | Define o primeiro ano como ano atual menos três |
| 11 | Define o último ano como ano anterior |
| 12 | Começa com uma página por ano para manter a primeira execução pequena |
| 13 | Pede cem trabalhos por página |
| 14-15 | Define um segundo de intervalo entre chamadas |
| 16 | `validate` concentra as regras dos parâmetros antes de consultar as fontes |
| 17-18 | Recusa anos fora da ordem, anteriores a 1900 e o ano ainda em andamento |
| 19-20 | Recusa páginas menores que um, tamanho fora de 1 a 100 e intervalo negativo |
| 21-22 | Exige chave para seguir o cursor além da primeira página, conforme a regra de acesso usada no projeto |

Os type hints, como `int` e `float`, mostram o tipo esperado para quem lê o código. Eles não substituem as validações. As exceções evitam gastar chamadas em uma configuração que já sabemos ser inválida.

## 7. Comunicação: `src/http_client.py`

| Linhas | Leitura do trecho |
|---|---|
| 1-10 | A docstring resume a função. Os imports trazem relógio, datas, leitura de cabeçalho HTTP, anotação de retorno e requests |
| 11-14 | `ApiError` é o erro do nosso cliente. As mensagens não copiam a URL autenticada nem o conteúdo recebido |
| 15-18 | A classe recebe intervalo e quantidade de tentativas; o padrão permite quatro chamadas por operação |
| 19 | A sessão reaproveita conexões, em vez de abrir uma sessão nova para cada chamada |
| 20 | O `User-Agent` identifica o projeto para o serviço |
| 21-22 | Guarda o instante da última chamada; começa sem uma chamada anterior |
| 23 | `get` recebe URL e parâmetros separados. O retorno pode ser lista ou objeto JSON |
| 24 | O laço limita a quantidade de tentativas |
| 25 | Espera apenas o que falta para atingir o intervalo mínimo. `max` evita tempo negativo |
| 26 | Atualiza o instante da chamada usando `monotonic`, um relógio apropriado para medir duração |
| 27-28 | Começa sem resposta e entra no tratamento de falhas da requisição |
| 29 | Faz GET com até dez segundos para conectar e sessenta para aguardar leitura |
| 30 | Se não for 429 nem 5xx, não trata a resposta como falha transitória |
| 31-32 | Outros erros HTTP, como 400 e 401, encerram a operação sem repetir o mesmo pedido |
| 33-34 | Tenta interpretar o corpo como JSON e retorna o resultado |
| 35-36 | Se o corpo não for JSON válido, retorna um erro curto, sem copiar HTML ou conteúdo externo |
| 37-38 | Timeout e falha de conexão podem ser temporários; o laço poderá tentar de novo |
| 39-40 | Outras falhas do requests recebem uma mensagem genérica e interrompem a operação |
| 41-42 | Se a última tentativa também falhou, encerra a coleta |
| 43 | Calcula a espera crescente: um, dois e quatro segundos entre as tentativas padrão |
| 44-45 | Se houve resposta HTTP, procura o cabeçalho `Retry-After` |
| 46-47 | Quando ele vem em segundos, usa o maior valor entre a espera calculada e o pedido da API |
| 48-51 | Se não for número, tenta interpretar uma data HTTP e calcula o tempo restante |
| 52-53 | Se o cabeçalho não puder ser interpretado, mantém a espera já calculada |
| 54 | Espera antes da próxima volta do laço |

O limite de taxa é local a esse cliente. Ele não controla outros programas usando o mesmo IP. Também não existe orçamento diário próprio no código; se a API negar acesso, a execução para depois das regras de tentativa.

## 8. Extração: `src/extract.py`

### Endpoints e dados usados

| Endpoint | Filtro ou conteúdo | Uso |
|---|---|---|
| `https://api.openalex.org/works` | País da instituição BR e ano de publicação | Trabalhos e contagem do filtro |
| `https://api.openalex.org/works/{id}` | ID individual | Autores completos nos casos com cem autores na listagem |
| `https://api.openalex.org/institutions` | Lista de IDs | Nome e localização da instituição |
| `https://servicodados.ibge.gov.br/api/v1/localidades/municipios` | Lista de municípios | Código, UF e região oficial |

| Linhas | Leitura do trecho |
|---|---|
| 1-10 | Explicam a intenção e importam JSON, ambiente, datas, caminhos, hashes, configuração e cliente HTTP |
| 11-15 | Definem as URLs em um só lugar; isso facilita identificar quais serviços são chamados |
| 16 | `save_json` é a função comum para gravar objetos no disco |
| 17 | Cria a pasta se necessário, inclusive as pastas anteriores no caminho |
| 18-20 | Grava JSON em UTF-8, preservando acentos e usando indentação para facilitar a leitura |
| 21-23 | `collect` valida os parâmetros e cria o cliente com o intervalo escolhido |
| 24 | Lê a chave do ambiente. Sem chave, envia um dicionário vazio; não usa um segredo fixo no código |
| 25-26 | Prepara a lista de trabalhos e a lista de cobertura anual |
| 27 | Percorre os anos incluindo o último ano informado; o `+ 1` é necessário porque `range` exclui o fim |
| 28 | O cursor inicial `*` pede a primeira página |
| 29-30 | Zera a contagem coletada e prepara o total informado pela fonte |
| 31 | Limita a quantidade de páginas do ano |
| 32-33 | Consulta trabalhos com país de instituição BR e o ano atual do laço |
| 34 | Ordena por data crescente e envia tamanho e cursor da página |
| 35-36 | `select` limita a resposta aos campos usados. Não baixa abstracts ou outros campos desnecessários |
| 37-38 | Confere se a resposta tem uma lista de resultados e a contagem esperada |
| 39 | Guarda `meta.count`, que representa o total do filtro daquele ano |
| 40 | Acrescenta os resultados à lista de trabalhos |
| 41 | Atualiza a quantidade recebida para esse ano |
| 42 | Lê o cursor da próxima página |
| 43-44 | Para se não houver cursor, se a página estiver vazia ou se a quantidade disponível já tiver sido atingida |
| 45-46 | Guarda ano, total disponível, total coletado e se a coleta chegou ao fim |
| 47-48 | Recusa uma execução inteiramente vazia em vez de publicar uma base sem trabalhos |
| 49-51 | Explicam o corte de autores e iniciam o contador de consultas de expansão |
| 52-53 | Inspecionam os trabalhos com cem ou mais autores. Mesmo um caso com exatamente cem pode ser consultado de novo; isso evita depender de um campo extra |
| 54 | Retira apenas o último trecho do ID do OpenAlex |
| 55 | Consulta o endpoint individual do trabalho, usando o mesmo cliente e a mesma regra de espera |
| 56 | Troca a lista de autores pela lista detalhada |
| 57 | Conta o trabalho expandido para registrar essa ação no manifesto |
| 58-60 | Percorre autores e instituições, guarda IDs brasileiros em um conjunto para remover repetidos e ordena os IDs |
| 61 | Prepara a lista das instituições detalhadas |
| 62 | Divide IDs em lotes de até cinquenta para reduzir a quantidade de chamadas |
| 63-64 | Consulta instituições com um filtro OR, representado por `|` entre os IDs |
| 65-66 | Pede nome, país e `geo`. O tamanho solicitado comporta o lote de até cinquenta IDs |
| 67 | Junta os resultados dos lotes |
| 68 | Busca os municípios do IBGE |
| 69-70 | Recusa uma resposta que não seja uma lista preenchida |
| 71-72 | Salva três arquivos: trabalhos, instituições e municípios. Mantém os dados recebidos para permitir reprocessar |
| 73-74 | Começa o manifesto e registra quando a coleta terminou, em UTC |
| 75 | Guarda URLs das fontes e os anos pedidos, sem parâmetros de autenticação |
| 76 | Descreve como o recorte foi escolhido |
| 77 | Guarda cobertura de cada ano e um indicador geral de coleta completa |
| 78 | Guarda quantidade de trabalhos expandidos e instituições pedidas e recebidas |
| 79-80 | Calcula SHA-256 de cada JSON de dados. O manifesto não calcula hash de si mesmo |
| 81-83 | Fecha o objeto, grava `manifest.json` e devolve os metadados para quem chamou |

Hash não comprova que a fonte está correta. Ele permite perceber se o arquivo local mudou depois da coleta. O manifesto em si não tem assinatura digital. O endpoint individual do OpenAlex também tem limites para trabalhos com muitos milhares de autores; o teste de afiliação brasileira continua importante depois da expansão.

## 9. Preparar o banco em memória: `src/transform.py`

| Linhas | Leitura do trecho |
|---|---|
| 1-7 | Apresentam o arquivo e importam JSON, caminhos e DuckDB |
| 8-10 | Descobrem a raiz do projeto a partir da localização do script, para encontrar o SQL |
| 11-12 | Criam uma conexão DuckDB em memória; não há servidor ou arquivo de banco permanente |
| 13-16 | Definem o schema de entrada dos trabalhos. Campos que ainda serão convertidos entram como texto; objetos aninhados entram como JSON |
| 17 | Define ID, nome, país e localização das instituições |
| 18-19 | Define os campos usados dos municípios; o código oficial entra como inteiro grande |
| 20-21 | Inicia o bloco de tratamento de erro e percorre os três schemas |
| 22 | Lê o arquivo JSON com colunas explícitas; isso reduz a dependência de inferência automática de tipos |
| 23 | Cria tabelas com prefixo `raw_` no banco em memória |
| 24-25 | Cria a tabela para os totais e a cobertura que vieram do manifesto |
| 26-28 | Se o manifesto estiver presente, abre seu JSON |
| 29-30 | Monta tuplas com ano, disponível, coletado e completo |
| 31-32 | Insere as tuplas com parâmetros, sem montar valores dentro do SQL |
| 33 | Executa as instruções de `sql/transform.sql` |
| 34 | Devolve a conexão aberta; a auditoria e a exportação ainda vão usar as tabelas |
| 35-37 | Se falhar nessa etapa, fecha a conexão e repassa o erro |

No pipeline normal o manifesto é obrigatório e seus hashes são conferidos antes desta função. A leitura opcional dentro da função ajuda nos testes pequenos de transformação, que não precisam sempre montar uma coleta inteira.

## 10. Tratamento no SQL: `sql/transform.sql`

| Linhas | Leitura do trecho |
|---|---|
| 1-2 | `normalizar` remove espaços nas pontas e acentos e coloca em minúsculas. Não corrige abreviações ou erros de digitação |
| 3-5 | Começa `works`, renomeia o ID e troca título vazio por nulo |
| 6 | Converte ano para inteiro |
| 7 | Converte a data para `DATE` |
| 8 | Converte citações para inteiro grande |
| 9 | Extrai `is_oa` do JSON e converte para booleano |
| 10 | Extrai o identificador do tema principal |
| 11 | Extrai o nome do tema e usa `Não informado` quando ele está ausente |
| 12-13 | Preserva o JSON de autores para abrir na etapa seguinte |
| 14 | Numera registros por ID e mantém um. A ordem por data e título dá um critério simples de escolha |
| 15-18 | Começa `affiliations` com pares distintos de trabalho e instituição |
| 19-20 | Extrai ID e nome da instituição dentro de cada item |
| 21-22 | `LATERAL json_each` abre os autores do trabalho atual |
| 23 | Abre a lista de instituições de cada autor |
| 24 | Mantém somente as instituições com país BR |
| 25-27 | Começa a tabela de municípios e renomeia ID e nome |
| 28 | Extrai a sigla da UF pelo caminho de região imediata e intermediária |
| 29 | Extrai o nome da UF |
| 30-31 | Extrai a região brasileira e conclui a leitura do IBGE |
| 32-34 | Começa a dimensão de instituições, com ID e nome |
| 35-36 | Extrai cidade e UF do objeto `geo` |
| 37-38 | Usa os detalhes das instituições e mantém apenas as brasileiras |
| 39 | Evita mais de uma linha para o mesmo ID de instituição |
| 40-43 | Começa `institution_geo` com os dados da instituição e os campos que serão encontrados no IBGE |
| 44-45 | Marca correspondência que precisou traduzir `Federal District` |
| 46 | Marca correspondência encontrada sem essa tradução; caixa e acentos ainda são normalizados |
| 47-48 | Se não há cidade ou UF, marca localização incompleta |
| 49 | Os demais casos que não encontraram município ficam como sem correspondência |
| 50-51 | Usa `LEFT JOIN` para preservar a instituição mesmo quando não há município encontrado |
| 52 | Compara o nome normalizado da cidade |
| 53-55 | Exige também UF. Faz a tradução específica do DF e aceita nome ou sigla da UF do IBGE |
| 56-59 | Começa `production` com dados do trabalho e da afiliação |
| 60 | Mantém cidade e UF originais para poder conferir o cruzamento |
| 61 | Acrescenta município, UF e região encontrados no IBGE |
| 62 | Se nem o detalhe da instituição voltou, registra `instituicao_nao_retornada` |
| 63-64 | Liga os trabalhos aos pares de afiliação pelo ID do trabalho |
| 65 | Acrescenta a geografia sem apagar afiliações que estejam sem localização |
| 66-69 | Começa `annual`. A CTE `totals` é uma etapa temporária da consulta |
| 70 | Conta trabalhos do recorte e soma citações antes de multiplicar linhas por afiliação |
| 71 | Conta campos de acesso aberto conhecidos e calcula sua média. `true` vale um e `false` vale zero; nulos não entram na média |
| 72 | Conta os trabalhos em acesso aberto |
| 73-74 | Agrupa os trabalhos por ano e fecha a CTE |
| 75-76 | Acrescenta a contagem nacional que veio do manifesto |
| 77 | Divide trabalhos coletados pelo total disponível. `nullif` evita divisão por zero |
| 78-79 | Usa `lag` para pegar o total do ano anterior e calcular variação nacional: atual/anterior menos um |
| 80-81 | Faz o mesmo para a contagem do recorte, em outra coluna |
| 82 | Liga os totais coletados à cobertura pelo ano. O primeiro ano fica sem variação anterior |
| 83-86 | Conta trabalhos distintos por ano e instituição. `GROUP BY ALL` agrupa pelas colunas que não têm função de agregação |
| 87-91 | Começa as localidades de município e converte o código para texto para caber junto dos outros níveis |
| 92-93 | Acrescenta linhas de estado na mesma estrutura |
| 94-95 | Acrescenta linhas de região. `UNION ALL` empilha os níveis; não soma os trabalhos |
| 96-98 | Conta trabalhos distintos por ano, nível e localidade. Isso evita repetir um trabalho com duas instituições no mesmo lugar |
| 99-101 | Divide a contagem local pelo total coletado do ano para calcular participação |
| 102-105 | Conta trabalhos e calcula acesso aberto por ano e tema principal; parte de `works`, sem repetir trabalhos por instituição |

### Por que `try_cast`?

Ele transforma um valor que não pode ser convertido em nulo, em vez de encerrar o SQL imediatamente. A auditoria pode então identificar o problema com uma regra clara, como data inválida. Isso não significa aceitar qualquer nulo: os campos obrigatórios continuam sendo verificados.

### Por que não preencher tudo com zero?

`citations = 0` significa que a fonte informou zero citações. `citations = NULL` significa que não sabemos. Misturar os dois altera a interpretação. Na soma, DuckDB ignora os nulos conhecidos; se todos forem nulos, a soma fica nula. As ausências também aparecem no relatório.

## 11. Qualidade: `src/quality.py`

| Linhas | Leitura do trecho |
|---|---|
| 1-5 | Apresentam a auditoria e importam DuckDB |
| 6-13 | Definem as chaves esperadas de cada tabela. Elas mudam conforme o que uma linha representa |
| 14-17 | `audit` recebe o banco e o manifesto e começa a lista de verificações |
| 18-21 | A função interna `check` registra nome, quantidade inválida, aprovação e gravidade |
| 22-24 | `scalar` executa uma consulta que retorna um único número; evita repetir o mesmo código de leitura |
| 25-27 | Lê nomes e tipos das colunas de `production` com `DESCRIBE` |
| 28-30 | Define os tipos obrigatórios usados na conferência de schema |
| 31 | Conta quantas colunas obrigatórias estão ausentes ou com tipo diferente |
| 32-33 | Prepara as métricas de tabelas e percorre a lista de chaves |
| 34-35 | Conta linhas e registra erro quando uma tabela esperada está vazia |
| 36 | Junta os nomes de chave para usar no agrupamento SQL |
| 37-39 | Conta registros excedentes em grupos repetidos e registra a verificação de unicidade |
| 40-42 | Lê as colunas da tabela e começa a contagem de nulos |
| 43 | Conta os nulos de cada coluna |
| 44 | Divide nulos por linhas. Se a tabela estiver vazia, registra nulo para evitar dividir por zero |
| 45-46 | Se a coluna faz parte da chave, qualquer nulo reprova essa regra |
| 47 | Guarda quantidade de linhas e proporção de nulos por coluna |
| 48-51 | Confere se os anos dos trabalhos ficam no período do manifesto |
| 52-53 | Confere se existe uma data válida e se o ano dela combina com o ano informado |
| 54 | Reprova citações negativas |
| 55-57 | Procura trabalhos sem ao menos uma afiliação brasileira depois de abrir os autores |
| 58-59 | Confere se o código de município é único |
| 60-62 | Confere os campos obrigatórios da hierarquia do IBGE |
| 63-64 | Compara linhas de afiliação e produção; um JOIN que multiplica ou perde pares gera diferença |
| 65-66 | Confere se a soma dos trabalhos por ano bate com o total de trabalhos distintos |
| 67-68 | Confere se a participação geográfica fica entre zero e um |
| 69-70 | Impede um total nacional informado menor que a quantidade de trabalhos coletada |
| 71-72 | Confere se a cobertura calculada está entre zero e um |
| 73-74 | Confere o intervalo da proporção de acesso aberto |
| 75-77 | Conta citações e acesso aberto ausentes como avisos; não preenche esses dados |
| 78-79 | Conta pares sem município como aviso |
| 80 | Registra o aviso de coleta parcial quando o limite de páginas não cobriu o filtro |
| 81-82 | Compara quantidade de instituições pedidas e retornadas e avisa se faltaram detalhes |
| 83-85 | Monta uma lista das instituições sem município para ajudar a investigar o motivo |
| 86 | Decide a aprovação geral usando apenas as regras com gravidade de erro |
| 87-89 | Monta o relatório com status, verificações, tabelas e quantidade de duplicatas removidas |
| 90-91 | Converte os resultados sem correspondência em objetos com nomes de campos |
| 92 | Inclui o manifesto da fonte para manter a ligação com a coleta |
| 93-99 | Registra as limitações junto do resultado, para que não fiquem só no README |

A proporção de nulos é medida para todas as colunas dessas tabelas. O limite é zero nas chaves obrigatórias. Nos campos opcionais, a proporção é informada e algumas ausências geram avisos; não existe um limite universal que faria sentido para toda coluna.

`passed` no relatório significa que os dados passaram nas regras implementadas. Não significa que todos os fatos da fonte foram verificados manualmente ou que a amostra é representativa.

## 12. Gravação: `src/persist.py`

| Linhas | Leitura do trecho |
|---|---|
| 1-8 | Explicam a função e importam caminhos, DuckDB e a gravação de JSON |
| 9-11 | Listam as cinco tabelas que serão exportadas; os nomes não vêm da entrada do usuário |
| 12 | `export` recebe o banco, a pasta nova e o relatório |
| 13 | Cria a pasta e falha se ela já existir. Isso evita sobrescrever uma execução |
| 14 | Grava a auditoria antes dos dados, inclusive quando ela tiver reprovado |
| 15-16 | Se a qualidade não passou, encerra sem começar a gravar Parquet |
| 17-18 | Percorre as tabelas dentro do tratamento de erro de exportação |
| 19-20 | Resolve o caminho e trata apóstrofos antes de colocar o destino no comando SQL |
| 21-23 | `COPY` escreve Parquet com Snappy e divide por `year` |
| 24-25 | Prepara o padrão para reler todos os arquivos daquela tabela |
| 26-27 | Conta as linhas nos arquivos. `hive_partitioning` recupera o ano a partir do nome da pasta |
| 28 | Conta as linhas da tabela original em memória |
| 29-30 | Se as contagens forem diferentes, considera a exportação inválida |
| 31-32 | Consulta os metadados do Parquet para descobrir a compressão usada |
| 33-34 | Se ela não for Snappy, interrompe a exportação |
| 35-39 | Marca o relatório como `failed_export` se alguma gravação ou conferência falhar e repassa o erro |

Uma exportação pode deixar arquivos parciais na pasta que falhou. Eles não devem ser usados como entrega válida. O apontador da última execução aprovada só muda depois que tudo termina; não há promessa de uma transação única envolvendo todos os arquivos.

## 13. Comando principal: `src/pipeline.py`

| Linhas | Leitura do trecho |
|---|---|
| 1-16 | Apresentam o fluxo e importam argumentos, hashes, JSON, logs, datas, caminhos, identificador aleatório e as funções de cada etapa |
| 17-19 | Criam o logger do módulo, que mostra o andamento no terminal |
| 20-21 | `load_manifest` abre o manifesto da coleta |
| 22-23 | Usa uma lista fixa dos três arquivos esperados, sem seguir nomes arbitrários do JSON |
| 24 | Recalcula o SHA-256 do arquivo local |
| 25-26 | Se ele for diferente do manifesto, interrompe o reprocessamento |
| 27-29 | Devolve o manifesto validado e separa a próxima função |
| 30-32 | `main` cria a configuração padrão e o leitor dos argumentos do terminal |
| 33-37 | Recebe período, páginas, tamanho de página e intervalo com os tipos esperados |
| 38 | Recebe uma pasta local opcional para reprocessar |
| 39-40 | Recebe a pasta de saída e interpreta os argumentos |
| 41 | Liga logs com nível e mensagem, sem incluir parâmetros das APIs |
| 42 | Cria um ID com horário UTC e seis caracteres aleatórios para reduzir chance de conflito |
| 43 | Define a pasta daquela execução dentro de `runs/` |
| 44 | Começa sem conexão para poder fechá-la com segurança no final |
| 45-48 | Se veio `--from-raw`, usa a pasta informada e avisa que não vai coletar |
| 49-52 | Caso contrário, cria o caminho dos brutos, informa a coleta e chama `collect` com os parâmetros |
| 53 | Confere o manifesto e os hashes, inclusive depois de uma coleta nova |
| 54 | Carrega os dados e executa o SQL |
| 55 | Roda as verificações de qualidade |
| 56-57 | Acrescenta ao relatório o ID da execução e o momento da geração |
| 58 | Grava a auditoria e os Parquets, com releitura |
| 59-61 | Prepara um apontador temporário para a execução aprovada |
| 62 | Substitui `latest.json` somente depois da conclusão da exportação |
| 63 | Mostra onde a entrega foi salva |
| 64-66 | Lista no terminal os avisos que ficaram no relatório |
| 67 | Devolve zero, o código de sucesso do programa |
| 68-70 | Em uma exceção, evita copiar mensagens de bibliotecas que poderiam conter URLs ou dados externos |
| 71-72 | Grava ID, estado de falha e classe do erro em `failure.json` |
| 73-74 | Mostra a classe do erro e a pasta e retorna um, indicando falha |
| 75-77 | Fecha a conexão se ela chegou a ser aberta, tanto no sucesso quanto na falha |
| 78-81 | Permite executar com `python -m src.pipeline`; `SystemExit` repassa o código ao terminal |

Os logs gerais são curtos. Para entender uma reprovação de qualidade, o detalhamento está no relatório. Falhas antes da auditoria só têm a classe registrada em `failure.json`; esse é um limite atual de diagnóstico, escolhido para não copiar mensagens externas com dados sensíveis.

## 14. O que significa cada coluna final

### `production`: um trabalho associado a uma instituição

| Campo | Significado e cuidado |
|---|---|
| `work_id` | Identificador do trabalho no OpenAlex |
| `title` | Título recebido; texto vazio vira nulo |
| `year` | Ano de publicação; está também na pasta da partição |
| `publication_date` | Data convertida para `DATE` |
| `citations` | Citações observadas no momento da coleta; pode repetir em várias afiliações |
| `is_oa` | Se a fonte marcou o trabalho como acesso aberto; nulo continua desconhecido |
| `topic_id` | ID do tema principal; pode estar ausente |
| `topic` | Nome do tema principal ou `Não informado` |
| `institution_id` | ID da instituição brasileira ligada ao trabalho |
| `institution_name` | Nome da instituição na afiliação do trabalho |
| `city_source` | Cidade original do cadastro da instituição |
| `state_source` | UF original; pode ser nome, sigla ou `Federal District` |
| `municipality_id` | Código oficial encontrado no IBGE |
| `municipality` | Nome oficial encontrado no IBGE |
| `state_code` | Sigla da UF encontrada no IBGE |
| `state` | Nome da UF encontrada no IBGE |
| `region` | Região brasileira encontrada no IBGE |
| `geo_status` | Como ficou o cruzamento: encontrado, traduzido, incompleto, sem correspondência ou sem detalhe da instituição |

### Tabelas de indicadores

| Tabela e campos | Como interpretar |
|---|---|
| `annual.year` | Ano do indicador |
| `annual.works_count` | Quantidade de trabalhos distintos coletados |
| `annual.citations` | Soma de citações dos trabalhos coletados; não usa a base multiplicada por afiliações |
| `annual.oa_known` | Quantos trabalhos têm resposta conhecida para acesso aberto |
| `annual.oa_share` | Proporção em acesso aberto entre os casos conhecidos |
| `annual.oa_count` | Quantos trabalhos foram marcados como acesso aberto |
| `annual.source_available_works` | Contagem do filtro brasileiro informada pela API |
| `annual.collection_coverage` | Coletados divididos pelo total informado pela API |
| `annual.national_growth_rate` | Total da API no ano dividido pelo do ano anterior, menos um |
| `annual.sample_growth_rate` | Contagem coletada no ano dividida pela do ano anterior, menos um |
| `institution_annual.year, institution_id, institution_name` | Identificam o ano e a instituição |
| `institution_annual.works_count` | Trabalhos distintos do recorte ligados à instituição |
| `geography.year, level, location_id, location_name` | Identificam ano, município/estado/região, código e nome |
| `geography.works_count` | Trabalhos distintos ligados à localidade |
| `geography.share_of_collected_works` | Participação nos trabalhos coletados daquele ano |
| `topics.year, topic_id, topic` | Identificam ano e tema principal |
| `topics.works_count, oa_share` | Contagem do tema e proporção conhecida em acesso aberto |

Nas variações, 0,04 representa 4%, e -0,04 representa queda de 4%. Essas taxas podem ser negativas ou maiores que um; o intervalo de zero a um vale para participações e cobertura, não para crescimento.

## 15. Testes, trecho por trecho

Os exemplos dos testes são inventados e pequenos. Isso permite saber o resultado esperado sem depender de mudanças nas APIs. `TemporaryDirectory` cria pastas temporárias; `Mock` e `patch` substituem serviços externos durante o teste.

### `tests/test_http_client.py`

| Linhas | O que está sendo conferido |
|---|---|
| 1-10 | Imports de unittest, mocks, requests e do cliente real que será testado |
| 11-15 | Monta uma resposta HTTP falsa com status, cabeçalhos e JSON |
| 16-18 | Declara a classe de testes |
| 19-25 | Simula 429 seguido de sucesso e exige que o cliente espere sete segundos pedidos no cabeçalho; a espera é substituída por mock |
| 26-33 | Simula timeout e 503 e confere que três tentativas configuradas realmente encerram com erro |
| 34-42 | Simula 401, confere que não repete e que a chave fictícia não aparece no texto da exceção |
| 43-51 | Controla o relógio e confere a espera mínima entre chamadas seguidas |
| 52-60 | Simula uma resposta que não pode virar JSON e espera `ApiError` |
| 61-64 | Permite executar o arquivo de teste diretamente |

### `tests/test_extract.py`

| Linhas | O que está sendo conferido |
|---|---|
| 1-12 | Imports de JSON, pasta temporária, unittest, caminhos, patch e funções da coleta |
| 13-16 | Monta um trabalho fictício com a quantidade desejada de autores |
| 17-19 | Declara a classe de testes |
| 20-29 | Substitui ambiente e cliente HTTP e prepara duas páginas, um lote de instituições e municípios |
| 30-36 | Executa a coleta, confere cursor e cobertura completa e procura a chave fictícia nos JSONs para confirmar que não foi salva |
| 37-46 | Prepara uma listagem com cem autores e um detalhe individual com outra instituição |
| 47-52 | Confere que a lista foi substituída antes de consultar os IDs das instituições |
| 53-57 | Remove variáveis do ambiente do teste e confere que mais páginas sem chave são recusadas |
| 58-62 | Confere recusa de período inválido e página acima do limite |
| 63-66 | Permite executar o arquivo diretamente |

### `tests/test_pipeline.py`

| Linhas | O que está sendo conferido |
|---|---|
| 1-15 | Imports dos recursos de teste e das funções reais do pipeline |
| 16-17 | Monta uma instituição brasileira fictícia |
| 18-24 | Monta um trabalho com ano, data, dez citações e autores |
| 25-31 | Prepara uma pasta temporária nova por teste e registra sua limpeza automática |
| 32-35 | Cria instituições na mesma cidade, em cidades homônimas de UFs diferentes e em uma cidade sem cadastro |
| 36-39 | Cria o pequeno cadastro fictício do IBGE com os mesmos nomes em duas UFs |
| 40-43 | Grava um trabalho repetido e uma afiliação repetida, além do segundo trabalho e das dimensões |
| 44-45 | Define o período e as contagens esperadas no manifesto de teste |
| 46-50 | Abre a transformação e registra o fechamento automático da conexão |
| 51-60 | Espera dois trabalhos e cinco pares; confere citações sem multiplicação e contagens geográficas distintas |
| 61-67 | Confere que a cidade sem cadastro continua no resultado e aparece no relatório, com proporção de nulos de 20% |
| 68-80 | Coloca uma data inválida e exige reprovação, relatório presente e nenhum Parquet publicado |
| 81-90 | Retira acesso aberto e citações de um trabalho e confere que os indicadores ficam nulos, sem inventar zero |
| 91-98 | Exporta os dados, verifica a pasta anual e relê a contagem dos arquivos |
| 99-110 | Simula total da API de mil para dois mil com um trabalho coletado por ano; exige variação nacional de 100% e variação do recorte de 0% |
| 111-124 | Simula Brasília e exige o código 5300108 e a marca de tradução da UF |
| 125-133 | Calcula hashes válidos, altera um bruto e exige erro na conferência de integridade |
| 134-137 | Permite executar o arquivo diretamente |

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Resultado conferido na entrega: **17 testes aprovados**. Isso cobre as regras testadas, mas não substitui a execução com dados reais. As duas formas de conferência foram usadas.

## 16. Conferir os arquivos entregues

1. Abra `output/latest.json` e veja o caminho da execução aprovada.
2. Abra `quality_report.json` naquela pasta. Confira `status`, `checks`, `tables` e `source_manifest`.
3. Em `checks`, olhe a gravidade: um aviso de coleta parcial não é uma aprovação de cobertura completa.
4. Em `tables`, confira linhas e `null_ratio`. Zero significa nenhum nulo naquela coluna; não significa qualidade perfeita da fonte.
5. Em `source_manifest`, veja período, seleção, cobertura por ano, fontes e hashes.
6. Confira as pastas das cinco tabelas e as partições por ano.

Para ler o resumo anual entregue sem fazer uma coleta nova, rode este exemplo na raiz do repositório:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
import duckdb

output = Path('output')
pointer = json.loads((output / 'latest.json').read_text())
files = output / pointer['path'] / 'annual' / '**' / '*.parquet'
connection = duckdb.connect()
connection.read_parquet(str(files), hive_partitioning=True).create_view('annual')
print(connection.execute('''
    SELECT year, source_available_works, works_count,
           collection_coverage, national_growth_rate, oa_share
    FROM annual ORDER BY year
''').fetchall())
connection.close()
PY
```

O exemplo lê o apontador, encontra os arquivos, recupera o ano das pastas, cria uma view e consulta as colunas escolhidas. Não precisa de chave ou internet, depois que as dependências estiverem instaladas.

A execução entregue tem 300 trabalhos, 591 pares e 209 instituições. As 41 verificações terminaram com quarenta aprovações e um aviso de coleta parcial. Os resultados comentados estão em [RESULTADOS.md](RESULTADOS.md).

## 17. Por que o README está dividido desse jeito?

| Parte do README | O que ela ajuda a entender |
|---|---|
| Abertura | Qual é a atividade e o que já foi entregue |
| Por que essas APIs | De onde vêm os dados e por que a combinação atende ao desafio |
| O que a análise cobre | Diferença entre total da API e recorte baixado |
| Como rodar | Primeiro comando, dependências e período da entrega |
| Chave do OpenAlex | Quando ela é necessária e como evitar colocá-la no Git |
| Reprocessar | Como reutilizar os brutos locais e quais arquivos foram publicados |
| Organização | Onde procurar cada responsabilidade |
| Tratamento | Quais transformações foram feitas e como não repetir trabalhos nas contagens |
| Qualidade e saída | O que reprova a execução, o que é aviso e onde os dados são gravados |
| Testes | Como conferir as regras sem depender das APIs |
| Problemas de execução | Onde olhar quando a coleta ou a validação falha |
| Requisitos | Como o avaliador encontra cada item pedido no desafio |

O README evita duplicar todo o código. Este guia faz a leitura detalhada; `APRENDIZADOS.md` registra os problemas reais; `RESULTADOS.md` interpreta os números. Assim cada documento tem um uso claro.

## 18. Erros reais, acertos e limites

Os ajustes de ordenação, autores truncados, Distrito Federal e contagem anual estão explicados em [APRENDIZADOS.md](APRENDIZADOS.md), com o motivo de cada correção. O histórico de commits mostra as mudanças em arquivos pequenos.

Ainda não há retomada por checkpoint, coleta distribuída, validação manual de campus ou fonte de financiamento. A lista de trabalhos fica em memória e o DuckDB usa um banco em memória. Isso foi suficiente para o recorte entregue. Antes de tentar baixar toda a base, seria preciso rever essa estratégia e planejar armazenamento, orçamento da API e retomada de falhas.

O próximo passo mais útil para a análise seria aumentar a cobertura e comparar períodos com cuidado. Acrescentar ferramentas sem resolver essa limitação não tornaria os resultados mais representativos.
