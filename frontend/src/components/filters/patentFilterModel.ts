import type {
  LandscapeActiveFilters,
  LandscapeQuery,
} from "../../types/landscape";

// Source authorities offered as quick toggles. The backend echoes the richer
// authority labels (e.g. "TURKPATENT/TPO") in responses, but the filter value
// itself is the short source token.
export const LANDSCAPE_SOURCES = ["USPTO", "EPO", "TURKPATENT"];

export interface LandscapeFilterFormState {
  sources: string[];
  publicationYearFrom: string;
  publicationYearTo: string;
  filingYearFrom: string;
  filingYearTo: string;
  country: string;
  assignee: string;
  keyword: string;
  applicationArea: string;
  classification: string;
}

export const EMPTY_LANDSCAPE_FILTER_FORM: LandscapeFilterFormState = {
  sources: [],
  publicationYearFrom: "",
  publicationYearTo: "",
  filingYearFrom: "",
  filingYearTo: "",
  country: "",
  assignee: "",
  keyword: "",
  applicationArea: "",
  classification: "",
};

function optionalNumber(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function optionalText(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

export function buildLandscapeQueryFromForm(
  form: LandscapeFilterFormState,
): LandscapeQuery {
  const query: LandscapeQuery = {};
  if (form.sources.length > 0) query.source = [...form.sources];

  const publicationYearFrom = optionalNumber(form.publicationYearFrom);
  const publicationYearTo = optionalNumber(form.publicationYearTo);
  const filingYearFrom = optionalNumber(form.filingYearFrom);
  const filingYearTo = optionalNumber(form.filingYearTo);

  if (publicationYearFrom !== undefined) {
    query.publication_year_from = publicationYearFrom;
  }
  if (publicationYearTo !== undefined) {
    query.publication_year_to = publicationYearTo;
  }
  if (filingYearFrom !== undefined) query.filing_year_from = filingYearFrom;
  if (filingYearTo !== undefined) query.filing_year_to = filingYearTo;

  const country = optionalText(form.country);
  const assignee = optionalText(form.assignee);
  const keyword = optionalText(form.keyword);
  const applicationArea = optionalText(form.applicationArea);
  const classification = optionalText(form.classification);

  if (country) query.country = [country];
  if (assignee) query.assignee = assignee;
  if (keyword) query.keyword = keyword;
  if (applicationArea) query.application_area = applicationArea;
  if (classification) query.classification = classification;

  return query;
}

// Inverse of buildLandscapeQueryFromForm: hydrate the editable form shape from an
// applied patent-filter query. Used to seed each view's local editing buffer from
// the shared (URL-backed) filter state without forking the filter model.
export function landscapeFormFromQuery(
  query: LandscapeQuery,
): LandscapeFilterFormState {
  return {
    sources: query.source
      ? LANDSCAPE_SOURCES.filter((source) => query.source!.includes(source))
      : [],
    publicationYearFrom:
      query.publication_year_from !== undefined
        ? String(query.publication_year_from)
        : "",
    publicationYearTo:
      query.publication_year_to !== undefined
        ? String(query.publication_year_to)
        : "",
    filingYearFrom:
      query.filing_year_from !== undefined
        ? String(query.filing_year_from)
        : "",
    filingYearTo:
      query.filing_year_to !== undefined ? String(query.filing_year_to) : "",
    country: query.country?.[0] ?? "",
    assignee: query.assignee ?? "",
    keyword: query.keyword ?? "",
    applicationArea: query.application_area ?? "",
    classification: query.classification ?? "",
  };
}

export function isLandscapeFilterFormEmpty(
  form: LandscapeFilterFormState,
): boolean {
  return (
    form.sources.length === 0 &&
    form.publicationYearFrom.trim() === "" &&
    form.publicationYearTo.trim() === "" &&
    form.filingYearFrom.trim() === "" &&
    form.filingYearTo.trim() === "" &&
    form.country.trim() === "" &&
    form.assignee.trim() === "" &&
    form.keyword.trim() === "" &&
    form.applicationArea.trim() === "" &&
    form.classification.trim() === ""
  );
}

export function hasActiveLandscapeFilters(
  filters: LandscapeActiveFilters,
): boolean {
  return Object.keys(filters).length > 0;
}

export function formatInteger(value: number): string {
  return new Intl.NumberFormat().format(value);
}

export function mergeOptions(
  ...optionGroups: Array<string[] | undefined>
): string[] {
  const seen = new Set<string>();
  const merged: string[] = [];
  for (const group of optionGroups) {
    for (const option of group ?? []) {
      const trimmed = option.trim();
      if (!trimmed || seen.has(trimmed)) continue;
      seen.add(trimmed);
      merged.push(trimmed);
    }
  }
  return merged;
}

export function countOptions(
  counts: Record<string, number> | undefined,
): string[] {
  return Object.keys(counts ?? {});
}

export function countSuffix(count: number | undefined): string {
  return count === undefined ? "" : ` (${formatInteger(count)})`;
}

export function yearPlaceholder(value: number | null | undefined): string {
  return value === null || value === undefined ? "Any" : String(value);
}

export function buildActiveFilterChips(
  filters: LandscapeActiveFilters,
): Array<{ key: string; label: string }> {
  const chips: Array<{ key: string; label: string }> = [];
  if (filters.source?.length) {
    chips.push({ key: "source", label: `Source: ${filters.source.join(", ")}` });
  }
  if (filters.publication_year_from !== undefined) {
    chips.push({
      key: "publication_year_from",
      label: `Publication from: ${filters.publication_year_from}`,
    });
  }
  if (filters.publication_year_to !== undefined) {
    chips.push({
      key: "publication_year_to",
      label: `Publication to: ${filters.publication_year_to}`,
    });
  }
  if (filters.filing_year_from !== undefined) {
    chips.push({
      key: "filing_year_from",
      label: `Filing from: ${filters.filing_year_from}`,
    });
  }
  if (filters.filing_year_to !== undefined) {
    chips.push({
      key: "filing_year_to",
      label: `Filing to: ${filters.filing_year_to}`,
    });
  }
  if (filters.country?.length) {
    chips.push({ key: "country", label: `Country: ${filters.country.join(", ")}` });
  }
  if (filters.assignee) {
    chips.push({ key: "assignee", label: `Assignee: ${filters.assignee}` });
  }
  if (filters.keyword) {
    chips.push({ key: "keyword", label: `Keyword: ${filters.keyword}` });
  }
  if (filters.application_area) {
    chips.push({
      key: "application_area",
      label: `Application area: ${filters.application_area}`,
    });
  }
  if (filters.classification) {
    chips.push({
      key: "classification",
      label: `Classification: ${filters.classification}`,
    });
  }
  return chips;
}
