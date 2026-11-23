-- {{raw}} aponta para o volume isolado desta execucao.
WITH works AS (
  SELECT id AS work_id, nullif(trim(display_name), '') AS title,
         try_cast(publication_year AS INT) AS year, try_cast(publication_date AS DATE) AS publication_date,
         try_cast(cited_by_count AS BIGINT) AS citations, open_access.is_oa AS is_oa,
         primary_topic.id AS topic_id, coalesce(primary_topic.display_name, 'Não informado') AS topic,
         authorships
  FROM read_files('{{raw}}/works.json', format => 'json', multiLine => true,
    schema => 'id STRING, display_name STRING, publication_year STRING, publication_date STRING, cited_by_count STRING, open_access STRUCT<is_oa:BOOLEAN>, primary_topic STRUCT<id:STRING,display_name:STRING>, authorships ARRAY<STRUCT<institutions:ARRAY<STRUCT<id:STRING,display_name:STRING,country_code:STRING>>>>')
  QUALIFY row_number() OVER (PARTITION BY id ORDER BY publication_date, display_name) = 1
), affiliations AS (
  SELECT w.work_id, i.id AS institution_id, min(i.display_name) AS institution_name
  FROM works w, LATERAL explode(w.authorships) a(author),
       LATERAL explode(a.author.institutions) inst(i)
  WHERE i.country_code = 'BR'
  GROUP BY w.work_id, i.id
), institutions AS (
  SELECT id, geo.city AS city_source, geo.region AS state_source
  FROM read_files('{{raw}}/institutions.json', format => 'json', multiLine => true,
    schema => 'id STRING, display_name STRING, country_code STRING, geo STRUCT<city:STRING,region:STRING>')
  WHERE country_code = 'BR'
  QUALIFY row_number() OVER (PARTITION BY id ORDER BY display_name) = 1
), municipalities AS (
  SELECT id AS municipality_id, nome AS municipality,
         `regiao-imediata`.`regiao-intermediaria`.UF AS uf
  FROM read_files('{{raw}}/municipalities.json', format => 'json', multiLine => true,
    schema => 'id BIGINT, nome STRING, `regiao-imediata` STRUCT<`regiao-intermediaria`:STRUCT<UF:STRUCT<sigla:STRING,nome:STRING,regiao:STRUCT<nome:STRING>>>>')
)
SELECT w.* EXCEPT (authorships), a.institution_id, a.institution_name,
       i.city_source, i.state_source, m.municipality_id, m.municipality,
       m.uf.sigla AS state_code, m.uf.nome AS state, m.uf.regiao.nome AS region,
       CASE WHEN i.id IS NULL THEN 'instituicao_nao_retornada'
            WHEN m.municipality_id IS NOT NULL AND lower(trim(i.state_source)) = 'federal district'
                 THEN 'correspondencia_uf_traduzida'
            WHEN m.municipality_id IS NOT NULL THEN 'correspondencia_exata'
            WHEN nullif(trim(i.city_source), '') IS NULL OR nullif(trim(i.state_source), '') IS NULL
                 THEN 'localizacao_incompleta'
            ELSE 'sem_correspondencia' END AS geo_status
FROM works w JOIN affiliations a USING (work_id)
LEFT JOIN institutions i ON i.id = a.institution_id
LEFT JOIN municipalities m
  ON trim(i.city_source) COLLATE UNICODE_CI_AI = trim(m.municipality) COLLATE UNICODE_CI_AI
 AND (CASE WHEN lower(trim(i.state_source)) = 'federal district' THEN 'Distrito Federal'
           ELSE trim(i.state_source) END) COLLATE UNICODE_CI_AI
     IN (m.uf.sigla COLLATE UNICODE_CI_AI, m.uf.nome COLLATE UNICODE_CI_AI)
