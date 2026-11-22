# O que apareceu nos dados

Coleta feita em **22/11/2026, às 09h20, horário de Brasília**. Os arquivos desta entrega estão na execução `20261122T122318Z-9ff025`, indicada em `output/latest.json`.

## Contagem nacional informada pelo OpenAlex

O filtro considera trabalhos com pelo menos uma instituição brasileira. A coluna de total vem da resposta da API, não da soma dos arquivos baixados.

| Ano | Total do filtro na API | Variação sobre o ano anterior | Trabalhos baixados | Cobertura da coleta |
|---|---:|---:|---:|---:|
| 2023 | 297.433 | - | 100 | 0,0336% |
| 2024 | 309.317 | +4,00% | 100 | 0,0323% |
| 2025 | 297.326 | -3,88% | 100 | 0,0336% |

A contagem indexada sobe em 2024 e fica menor em 2025. Isso não basta para dizer que a pesquisa no país cresceu ou caiu na mesma proporção. A base recebe atualizações, e trabalhos mais recentes podem levar tempo para entrar. A consulta também não explica as causas dessa variação.

## O recorte que foi tratado

Foram baixados **300 trabalhos**, que geraram **591 pares de trabalho e instituição**, ligados a **209 instituições brasileiras**. A listagem cortou os autores de nove trabalhos; nesses casos, foi preciso consultar o registro individual para recuperar as afiliações.

A coleta pega os primeiros 100 trabalhos de cada ano por data de publicação. Ela não é uma amostra aleatória. Os resultados abaixo descrevem apenas esse recorte.

| Ano | Trabalhos | Em acesso aberto | Proporção em acesso aberto | Citações observadas na coleta |
|---|---:|---:|---:|---:|
| 2023 | 100 | 92 | 92% | 11.034 |
| 2024 | 100 | 93 | 93% | 10.848 |
| 2025 | 100 | 93 | 93% | 6.585 |

O campo de acesso aberto estava preenchido nos 300 trabalhos. As citações refletem o momento da consulta. Trabalhos mais antigos tiveram mais tempo para receber citações; por isso, não uso essa diferença como comparação direta de qualidade.

### Instituições e regiões

No recorte dos três anos, as maiores contagens foram USP (61 trabalhos), Unicamp (18), Fiocruz (15), UFRJ (15) e UFSCar (14). Um mesmo trabalho pode contar para mais de uma instituição.

| Região | Trabalhos em 2023 | Trabalhos em 2024 | Trabalhos em 2025 |
|---|---:|---:|---:|
| Sudeste | 59 | 66 | 66 |
| Sul | 23 | 22 | 25 |
| Nordeste | 23 | 22 | 24 |
| Centro-Oeste | 16 | 11 | 9 |
| Norte | 4 | 9 | 7 |

O Sudeste aparece mais nesse recorte, mas a cobertura é pequena para transformar isso em uma conclusão sobre toda a produção do país. As colunas podem somar mais de 100: um trabalho com instituições de duas regiões aparece nas duas.

Os municípios e estados estão detalhados na tabela `geography`. A participação de cada localidade usa como denominador os 100 trabalhos coletados no respectivo ano.

### Temas

Entre os temas principais, apareceram `Artificial Intelligence in Education` (7 trabalhos) e `Education Pedagogy and Practices` (6). Isso abre uma possibilidade de estudo sobre educação e IA, mas os números ainda são pequenos. Não dá para dizer que esses sejam os temas mais pesquisados no Brasil com base nesta coleta.

## Como ficou a qualidade

- 41 verificações: 40 passaram e uma gerou o aviso esperado de coleta parcial.
- Nenhum trabalho repetido por ID na coleta final.
- Nenhum par repetido de trabalho e instituição na base tratada.
- Todos os 591 pares receberam município, UF e região.
- Desses pares, 24 usaram a tradução explícita de `Federal District` para `Distrito Federal`; os outros 567 usaram cidade e UF sem essa tradução.
- Os 15 arquivos Parquet foram relidos, com conferência das contagens e da compressão Snappy.

O relatório guarda a proporção de nulos de cada coluna. Campos opcionais, como tema principal, podem continuar ausentes; isso não é preenchido com informação inventada. Encontrar uma correspondência no IBGE também não prova que o campus do autor fica naquele município: a localização vem do cadastro da instituição.

## Próximo passo possível

Uma continuação seria aumentar a coleta com chave própria e comparar a cobertura por ano antes de interpretar rankings ou tendências dos temas. Para falar de financiamento ou incentivos à pesquisa, seria necessária outra fonte. Os dados atuais não respondem essa pergunta.
