# O que eu encontrei nos dados

Eu fiz a coleta em **22/11/2026, às 09h20, horário de Brasília**. Mantive os arquivos da entrega na execução `20261122T122318Z-9ff025`, indicada em `output/latest.json`.

## Como eu acompanhei a contagem nacional

Eu filtrei trabalhos com pelo menos uma instituição brasileira. Para o total de cada ano, usei a contagem informada pela API, sem somar as páginas baixadas como se fossem o país inteiro.

| Ano | Total do filtro na API | Variação sobre o ano anterior | Trabalhos baixados | Cobertura da coleta |
|---|---:|---:|---:|---:|
| 2023 | 297.433 | - | 100 | 0,0336% |
| 2024 | 309.317 | +4,00% | 100 | 0,0323% |
| 2025 | 297.326 | -3,88% | 100 | 0,0336% |

Eu observei uma contagem indexada maior em 2024 e menor em 2025. Não usei essa diferença para afirmar que a pesquisa no país cresceu ou caiu na mesma proporção. Considerei que a base recebe atualizações e que trabalhos recentes podem levar tempo para entrar. Também não tenho dados para explicar as causas dessa variação.

## Qual recorte eu tratei

Eu baixei **300 trabalhos** e, depois de abrir as afiliações, obtive **591 pares de trabalho e instituição**, ligados a **209 instituições brasileiras**. Consultei o registro individual de nove trabalhos para recuperar os autores cortados na listagem.

Eu selecionei os primeiros 100 trabalhos de cada ano por data de publicação. Como não fiz uma amostra aleatória, usei os resultados abaixo apenas para descrever esse recorte.

| Ano | Trabalhos | Em acesso aberto | Proporção em acesso aberto | Citações observadas na coleta |
|---|---:|---:|---:|---:|
| 2023 | 100 | 92 | 92% | 11.034 |
| 2024 | 100 | 93 | 93% | 10.848 |
| 2025 | 100 | 93 | 93% | 6.585 |

Eu conferi que o campo de acesso aberto estava preenchido nos 300 trabalhos. Registrei as citações do momento da consulta e considerei que trabalhos mais antigos tiveram mais tempo para recebê-las. Por isso, não usei essa diferença como comparação direta de qualidade.

### O que eu encontrei nas instituições e regiões

No recorte dos três anos, eu encontrei as maiores contagens na USP (61 trabalhos), Unicamp (18), Fiocruz (15), UFRJ (15) e UFSCar (14). Contei um mesmo trabalho em cada instituição à qual ele estava ligado.

| Região | Trabalhos em 2023 | Trabalhos em 2024 | Trabalhos em 2025 |
|---|---:|---:|---:|
| Sudeste | 59 | 66 | 66 |
| Sul | 23 | 22 | 25 |
| Nordeste | 23 | 22 | 24 |
| Centro-Oeste | 16 | 11 | 9 |
| Norte | 4 | 9 | 7 |

Eu encontrei mais trabalhos ligados ao Sudeste nesse recorte, mas não generalizei essa leitura para o país. Também não espero que as colunas somem 100: contei um trabalho nas duas regiões quando havia instituições das duas ligadas a ele.

Eu deixei os municípios e estados detalhados na tabela `geography`. Para a participação de cada localidade, usei como denominador os 100 trabalhos coletados no respectivo ano.

### O que eu encontrei nos temas

Eu encontrei `Artificial Intelligence in Education` (7 trabalhos) e `Education Pedagogy and Practices` (6) entre os temas principais. Vejo uma possibilidade de continuar o estudo em educação e IA, mas não concluí que esses sejam os temas mais pesquisados no Brasil com base nessa coleta pequena.

## Como eu conferi a qualidade

- Executei 41 verificações: 40 passaram e uma registrou o aviso esperado de coleta parcial.
- Não encontrei trabalhos repetidos por ID na coleta final.
- Não encontrei pares repetidos de trabalho e instituição na base tratada.
- Consegui associar os 591 pares a município, UF e região.
- Usei a tradução de `Federal District` para `Distrito Federal` em 24 pares; nos outros 567, cruzei cidade e UF sem essa tradução.
- Reli os 15 Parquets e conferi as contagens e a compressão Snappy.

Eu registrei a proporção de nulos de cada coluna no relatório. Mantive os campos opcionais ausentes, como tema principal, sem inventar informação para preenchê-los. Também não considerei uma correspondência no IBGE como prova do campus do autor: usei a localização cadastrada da instituição.

## Por onde eu continuaria

Eu começaria aumentando a coleta com chave própria e comparando a cobertura dos anos antes de interpretar rankings ou tendências dos temas. Para estudar financiamento ou incentivos à pesquisa, eu precisaria acrescentar uma fonte específica, porque não busquei esses dados nesta atividade.
