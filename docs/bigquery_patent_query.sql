-- Fiber-based wearable electronics: real EP (+ best-effort TR) patent records
-- Source: public dataset `patents-public-data.patents.publications` (Google BigQuery)
-- Run in the BigQuery console (sandbox is free, no credit card). Then
-- save the results as CSV and follow docs/collection_workflow.md to normalize,
-- validate, deduplicate, and review candidates before changing the corpus.
--
-- All patent fields below are verbatim from the public dataset; keywords and
-- candidate_application_areas are derived later from the real title/abstract.

WITH ep AS (
  SELECT
    REPLACE(publication_number, '-', '') AS publication_number,
    country_code,
    (SELECT t.text FROM UNNEST(title_localized) t WHERE t.language = 'en' LIMIT 1) AS title,
    (SELECT a.text FROM UNNEST(abstract_localized) a WHERE a.language = 'en' LIMIT 1) AS abstract,
    ARRAY_TO_STRING(ARRAY(
      SELECT DISTINCT x.name FROM UNNEST(assignee_harmonized) x WHERE x.name IS NOT NULL), '; ') AS assignee,
    ARRAY_TO_STRING(ARRAY(
      SELECT DISTINCT x.name FROM UNNEST(inventor_harmonized) x WHERE x.name IS NOT NULL), '; ') AS inventors,
    CAST(publication_date AS STRING) AS publication_date,
    CAST(filing_date AS STRING) AS filing_date,
    ARRAY_TO_STRING(ARRAY(SELECT DISTINCT c.code FROM UNNEST(ipc) c), '; ') AS ipc_codes,
    ARRAY_TO_STRING(ARRAY(SELECT DISTINCT c.code FROM UNNEST(cpc) c), '; ') AS cpc_codes,
    EXISTS(SELECT 1 FROM UNNEST(cpc) c
           WHERE REGEXP_CONTAINS(c.code, r'^(D03D|D04B|D04H|D06M|D10B|D02G|A41D|A41B)')) AS has_textile_cpc
  FROM `patents-public-data.patents.publications`
  WHERE country_code IN ('EP', 'TR')
)
SELECT
  publication_number, country_code, title, abstract, assignee, inventors,
  publication_date, filing_date, ipc_codes, cpc_codes
FROM ep
WHERE title IS NOT NULL AND abstract IS NOT NULL
  AND assignee != '' AND inventors != ''
  AND (
    (has_textile_cpc AND REGEXP_CONTAINS(LOWER(CONCAT(title, ' ', abstract)),
        r'conduct|electrod|sensor|electronic|electric|piezo|tribo|capacit|ecg|emg|eeg|antenna|circuit|signal|monitor|heating|rfid|battery|biopotential|strain|pressure'))
    OR REGEXP_CONTAINS(LOWER(CONCAT(title, ' ', abstract)),
        r'conductive textile|smart textile|e-textile|electronic textile|textile electrode|textile sensor|conductive yarn|wearable textile|textile antenna|smart garment|fabric sensor|knitted sensor|woven sensor|electronic fabric|conductive fabric')
  )
LIMIT 3000
