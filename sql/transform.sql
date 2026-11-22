-- Normalização conservadora: acentos e caixa não devem impedir um JOIN.
CREATE MACRO normalizar(texto) AS lower(strip_accents(trim(texto)));

CREATE TABLE works AS
SELECT id AS work_id, nullif(trim(display_name), '') AS title,
       try_cast(publication_year AS INTEGER) AS year,
       try_cast(publication_date AS DATE) AS publication_date,
       try_cast(cited_by_count AS BIGINT) AS citations,
       try_cast(json_extract_string(open_access, '$.is_oa') AS BOOLEAN) AS is_oa,
       json_extract_string(primary_topic, '$.id') AS topic_id,
       coalesce(json_extract_string(primary_topic, '$.display_name'), 'Não informado') AS topic,
       authorships
FROM raw_works
QUALIFY row_number() OVER (PARTITION BY id ORDER BY publication_date, display_name) = 1;

-- A mesma instituição aparece em vários autores: DISTINCT evita dupla contagem.
CREATE TABLE affiliations AS
SELECT DISTINCT w.work_id,
       json_extract_string(i.value, '$.id') AS institution_id,
       json_extract_string(i.value, '$.display_name') AS institution_name
FROM works w,
     LATERAL json_each(w.authorships) a,
     LATERAL json_each(a.value, '$.institutions') i
WHERE json_extract_string(i.value, '$.country_code') = 'BR';

CREATE TABLE municipalities AS
SELECT id AS municipality_id, nome AS municipality,
       json_extract_string("regiao-imediata", '$."regiao-intermediaria".UF.sigla') AS state_code,
       json_extract_string("regiao-imediata", '$."regiao-intermediaria".UF.nome') AS state,
       json_extract_string("regiao-imediata", '$."regiao-intermediaria".UF.regiao.nome') AS region
FROM raw_municipalities;

CREATE TABLE institutions AS
SELECT id AS institution_id, display_name AS institution_name,
       json_extract_string(geo, '$.city') AS city,
       json_extract_string(geo, '$.region') AS state_source
FROM raw_institutions
WHERE country_code = 'BR'
QUALIFY row_number() OVER (PARTITION BY id ORDER BY display_name) = 1;

-- Não uso apenas o nome da cidade: existem municípios homônimos em UFs distintas.
CREATE TABLE institution_geo AS
SELECT i.*, m.municipality_id, m.municipality, m.state_code, m.state, m.region,
       CASE WHEN m.municipality_id IS NOT NULL AND normalizar(i.state_source) = 'federal district'
                 THEN 'correspondencia_uf_traduzida'
            WHEN m.municipality_id IS NOT NULL THEN 'correspondencia_exata'
            WHEN nullif(i.city, '') IS NULL OR nullif(i.state_source, '') IS NULL
                 THEN 'localizacao_incompleta'
            ELSE 'sem_correspondencia' END AS geo_status
FROM institutions i
LEFT JOIN municipalities m
  ON normalizar(i.city) = normalizar(m.municipality)
 -- O OpenAlex usa esse nome em inglês para o Distrito Federal.
 AND CASE WHEN normalizar(i.state_source) = 'federal district' THEN 'distrito federal'
          ELSE normalizar(i.state_source) END IN (normalizar(m.state), normalizar(m.state_code));

CREATE TABLE production AS
SELECT w.work_id, w.title, w.year, w.publication_date, w.citations, w.is_oa,
       w.topic_id, w.topic, a.institution_id, a.institution_name,
       g.city AS city_source, g.state_source, g.municipality_id,
       g.municipality, g.state_code, g.state, g.region,
       coalesce(g.geo_status, 'instituicao_nao_retornada') AS geo_status
FROM works w
JOIN affiliations a USING (work_id)
LEFT JOIN institution_geo g USING (institution_id);

-- Uso meta.count para o total nacional e works para as métricas do recorte, sem repetir afiliações.
CREATE TABLE annual AS
WITH totals AS (
    SELECT year, count(*) AS works_count, sum(citations) AS citations,
           count(is_oa) AS oa_known, avg(is_oa::INTEGER) AS oa_share,
           count(*) FILTER (WHERE is_oa) AS oa_count
    FROM works GROUP BY year
)
-- O crescimento nacional usa meta.count, enquanto acesso aberto e citações usam o recorte.
SELECT t.*, c.available AS source_available_works,
       t.works_count::DOUBLE / nullif(c.available, 0) AS collection_coverage,
       c.available::DOUBLE / nullif(lag(c.available) OVER (ORDER BY t.year), 0) - 1
          AS national_growth_rate,
       t.works_count::DOUBLE / nullif(lag(t.works_count) OVER (ORDER BY t.year), 0) - 1
          AS sample_growth_rate
FROM totals t LEFT JOIN raw_coverage c USING (year);

CREATE TABLE institution_annual AS
SELECT year, institution_id, institution_name, count(DISTINCT work_id) AS works_count
FROM production GROUP BY ALL;

CREATE TABLE geography AS
WITH locations AS (
    SELECT year, work_id, 'municipio' AS level, municipality_id::VARCHAR AS location_id,
           municipality AS location_name FROM production WHERE municipality_id IS NOT NULL
    UNION ALL
    SELECT year, work_id, 'estado', state_code, state FROM production WHERE state_code IS NOT NULL
    UNION ALL
    SELECT year, work_id, 'regiao', region, region FROM production WHERE region IS NOT NULL
), counts AS (
    SELECT year, level, location_id, location_name, count(DISTINCT work_id) AS works_count
    FROM locations GROUP BY ALL
)
SELECT c.*, c.works_count::DOUBLE / a.works_count AS share_of_collected_works
FROM counts c JOIN annual a USING (year);

CREATE TABLE topics AS
SELECT year, topic_id, topic, count(*) AS works_count, avg(is_oa::INTEGER) AS oa_share
FROM works GROUP BY ALL;
