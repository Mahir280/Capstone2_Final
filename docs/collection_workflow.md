# Reproducible Patent Collection Workflow

This document describes how to reproduce and extend the public-data collection
method without relying on private contributor shards or one-off helper scripts.
The running application does not fetch patent-office data. It loads the reviewed
canonical corpus at `data/raw/fiber_wearable_patents_sources.csv`.

## Source Query

1. Open Google BigQuery and select the public
   `patents-public-data.patents.publications` dataset.
2. Run `docs/bigquery_patent_query.sql`.
3. Record the query date and keep an unchanged local export of the result.
4. Export the result as CSV. The raw export is an intermediate file and should
   not be committed to the application repository.

The included query selects English-title and English-abstract EP and TR
publications, retains the public patent fields needed by the project, and
applies textile/electronics relevance terms. The `LIMIT` clause makes the
maximum result size explicit and can be adjusted for a documented rerun.

## Normalize To The Canonical Schema

Map each exported row to the 18-column schema documented in
`docs/canonical_corpus.md`:

1. Preserve publication number, title, abstract, assignee, inventors,
   publication date, filing date, IPC codes, and CPC codes from BigQuery.
2. Set `source` from the publication authority (`EPO` for EP records and
   `TURKPATENT` for TR records).
3. Use the normalized publication number for both `patent_id` and
   `publication_number`.
4. Build `source_url` from a verifiable public patent page, such as
   `https://patents.google.com/patent/<PUBLICATION_NUMBER>/en`.
5. Derive concise `keywords` and `candidate_application_areas` only from the
   stored title and abstract. Do not invent patent facts.
6. Leave optional values blank when they are not present in the source. Never
   use filler such as `Unknown`, `N/A`, `TBD`, or `placeholder`.

When spreadsheet software is used for the transformation, import and export as
UTF-8 CSV, preserve the header order exactly, and quote fields containing
commas, quotes, or newlines.

## Quality Gate

Before a candidate can enter the canonical corpus, verify that:

- all required fields listed in `docs/canonical_corpus.md` are non-empty;
- at least one IPC or CPC classification is present;
- the source authority and country values are normalized;
- the source URL resolves to the stated publication;
- the title, abstract, dates, assignee, and inventors agree with the source;
- the record is relevant to fiber-based wearable electronics;
- the publication number does not already exist in the canonical corpus; and
- the candidate is not synthetic, illustrative, or mock data.

Candidates that fail the gate belong in
`data/raw/patent_collection_review_needed.csv`, with `review_reason`,
`missing_fields`, and `source_notes` completed. Review-queue rows are not part
of the accepted corpus.

## Merge And Verification

Work on a copy of the canonical CSV and keep the committed corpus unchanged
until review is complete.

1. Append only accepted, schema-aligned candidates.
2. Deduplicate by normalized publication number and preserve source authority.
3. Sort or retain row order consistently so the resulting diff can be reviewed.
4. Confirm the final CSV has the exact canonical header and no blank required
   fields in newly added rows.
5. Confirm no review-queue publication number appears in the accepted corpus.
6. Run the repository tests and quality checks described in `README.md`.
7. Review the corpus diff before replacing the canonical file.

For a reproducibility record, retain the BigQuery SQL, query date, raw export
checksum, accepted/rejected counts, and the validation criteria used. Raw
exports and temporary transformation files should remain outside the public
application repository.
