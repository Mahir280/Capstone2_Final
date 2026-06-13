# Canonical Patent Corpus

`data/raw/fiber_wearable_patents_sources.csv` is the single canonical raw patent
corpus for this project. It is the prepared corpus loaded by the Dataset
Coverage workflow and the recovery/demo loading path.

This repository does not contain live patent-office integrations, scraped search
results, or exhaustive office-wide coverage. The corpus is a curated project
corpus: the earliest records were collected before the final expansion schema
was enforced, and later expansion batches were validated against the strict
quality gate before merging. Future collection should preserve the existing
curated corpus across USPTO, EPO, and TURKPATENT/TPO without adding unverified
or synthetic records.

## Final Schema

Accepted corpus rows use these columns, in this order:

1. `source`
2. `patent_id`
3. `publication_number`
4. `title`
5. `abstract`
6. `assignee`
7. `inventors`
8. `publication_date`
9. `filing_date`
10. `country`
11. `source_url`
12. `keywords`
13. `candidate_application_areas`
14. `ipc_codes`
15. `cpc_codes`
16. `claims_excerpt`
17. `patent_family`
18. `citation_count`

The loader may preserve extra columns and may map model-supported fields into
the current internal patent model. In the current model, `publication_number`
can serve as the publication-style `patent_id`, `claims_excerpt` maps to
`claims_text`, and `ipc_codes` and `cpc_codes` normalize into list fields.
`candidate_application_areas`, `patent_family`, and `citation_count` are corpus
metadata until the storage model explicitly supports them.

## Accepted Sources

Canonical accepted source authorities are:

- `USPTO`
- `EPO`
- `TURKPATENT` or `TPO`

Source labels should remain explicit and normalized. Do not describe the corpus
as exhaustive coverage of any patent office.

## Accepted-Record Rules

Future records accepted into the canonical corpus must have non-empty,
verified values for:

- `source`
- `patent_id`
- `publication_number`
- `title`
- `abstract`
- `assignee`
- `inventors`
- `publication_date`
- `filing_date`
- `country`
- `source_url`
- `keywords`
- `candidate_application_areas`

At least one of `ipc_codes` or `cpc_codes` must be present.

These fields are strongly preferred and may be blank only when the source cannot
provide them:

- `claims_excerpt`
- `patent_family`
- `citation_count`

Do not use `Unknown`, `N/A`, `TBD`, `placeholder`, or similar literal filler in
the corpus. Leave unverified optional fields blank and send records with missing
critical data to review instead of diluting the canonical corpus.

## Review-Needed File

`data/raw/patent_collection_review_needed.csv` is the holding template for
future candidate records that fail the accepted-record rules. It uses the final
18-column schema plus:

- `review_reason`
- `missing_fields`
- `source_notes`

Rows in the review-needed file are not accepted corpus records. They should be
resolved, enriched, or rejected before anything moves into the canonical corpus.

## Current Corpus

The current canonical corpus contains 1166 curated patent records: 508 USPTO
records, 654 EPO records, and 4 TURKPATENT records. The corpus was expanded
from the original 273-record dataset through reviewed collection batches that
passed relevance, schema, and deduplication checks. The latest expansion added
490 real EPO records drawn from the public
`patents-public-data.patents.publications` dataset on Google BigQuery (see
`docs/bigquery_patent_query.sql`); every patent field is verbatim from that
dataset, and each row passed the required-field, classification, relevance, and
deduplication checks described in this document before inclusion. It remains
loadable as the prepared corpus and the sample/recovery corpus. The recovery
path reloads
`data/raw/fiber_wearable_patents_sources.csv`; it does not load a separate demo
CSV.

The current corpus should not be rejected solely because some records predate
the final quality gate or lack future metadata such as application areas,
classification codes, patent family, citation count, or claims excerpts.

New collection work should use the final schema and quality gate from the start.
Do not add synthetic rows, scrape records directly into the corpus, or invent
missing values.
