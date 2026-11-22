# Tentativas, ajustes e o que ficou de aprendizado

Este arquivo registra problemas que apareceram de verdade durante a implementação. As correções estão em commits separados para dar para acompanhar o caminho.

## 1. A API não aceitou a ordenação por ID

A primeira versão tentou usar `sort=id:asc`. Na consulta real, o OpenAlex respondeu com HTTP 400.

Troquei para `publication_date:asc`, que foi aceita. Também registrei essa escolha no manifesto. Isso tem um efeito na análise: a coleta limitada pega primeiro os trabalhos do começo do ano. Ela não pode ser tratada como amostra aleatória.

**O que ficou:** conferir o parâmetro com uma chamada pequena antes de ampliar a coleta.

## 2. Três trabalhos ficaram sem instituição brasileira

O filtro buscava trabalhos ligados ao Brasil, mas a auditoria encontrou três sem afiliação brasileira nos dados recebidos. Em vez de retirar a verificação, fui conferir a resposta.

A listagem do OpenAlex mostra só os primeiros 100 autores. A instituição brasileira podia estar depois desse corte. A solução foi consultar o trabalho individual quando a lista chegava a 100 autores. Nove trabalhos precisaram dessa consulta; depois disso, todos tinham afiliação brasileira disponível.

A regra está em `src/extract.py`, com teste em `tests/test_extract.py`. A [documentação de autorias](https://help.openalex.org/data/authorships/) explica esse limite.

**O que ficou:** o resultado de uma listagem pode trazer menos detalhes que o registro individual. Um filtro correto não garante que todas as informações venham na resposta.

## 3. Brasília não encontrou município no JOIN

A primeira conferência completa deixou 24 pares sem município. Ao olhar os nomes, todos estavam ligados a Brasília: o OpenAlex usava `Federal District`, enquanto o IBGE usava `Distrito Federal`.

Adicionei uma tradução específica no SQL e marquei esses casos como `correspondencia_uf_traduzida`. Preferi isso a tentar adivinhar nomes parecidos. As cidades continuam sendo cruzadas junto com a UF, porque há municípios homônimos.

**O que ficou:** guardar as linhas sem correspondência ajuda a descobrir a causa do problema. Apagar essas linhas esconderia parte dos dados.

## 4. Cem trabalhos por ano não mostram crescimento nacional

A coleta padrão baixa 100 trabalhos por ano. Comparar só essa contagem daria variação de 0%, criada pelo próprio limite da coleta.

O OpenAlex informa o total do filtro em `meta.count`. Usei esse valor para a série nacional e deixei os demais indicadores ligados ao recorte. O resumo anual guarda as duas contagens e a cobertura. Um teste usa totais nacionais diferentes com páginas do mesmo tamanho para conferir essa separação.

**O que ficou:** antes de calcular um indicador, é preciso entender como a coleta limita o que ele pode mostrar.

## Escolhas para manter o projeto simples

- DuckDB resolve o SQL e o Parquet sem um serviço de banco separado.
- Os scripts têm uma responsabilidade cada, com comentários sobre as regras menos óbvias.
- Os testes usam dados pequenos e respostas simuladas; não dependem da API estar disponível.
- Dados desconhecidos continuam nulos. Zero teria outro significado.
- O relatório sai junto dos dados e mostra avisos, inclusive quando o programa termina sem erro.
- Cada execução usa sua própria pasta. Uma falha não substitui a última entrega aprovada.

Ainda há limites: não há retomada de uma coleta interrompida nem execução distribuída. Os dados deste desafio cabem em memória. Se o volume crescer bastante, será preciso rever a coleta e o processamento antes de aumentar os limites sem cuidado.
