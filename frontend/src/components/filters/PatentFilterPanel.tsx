import { ApiError } from "../../api/client";
import { Callout } from "../common/Callout";
import { SectionCard } from "../common/SectionCard";
import type { LandscapeActiveFilters } from "../../types/landscape";
import type { FilterOptionsResponse } from "../../types/patents";
import {
  LANDSCAPE_SOURCES,
  buildActiveFilterChips,
  countOptions,
  countSuffix,
  formatInteger,
  hasActiveLandscapeFilters,
  isLandscapeFilterFormEmpty,
  mergeOptions,
  yearPlaceholder,
  type LandscapeFilterFormState,
} from "./patentFilterModel";

interface PatentFilterPanelProps {
  form: LandscapeFilterFormState;
  metadata: FilterOptionsResponse | undefined;
  metadataError: unknown;
  metadataIsLoading: boolean;
  activeFilters: LandscapeActiveFilters;
  filteredCount: number;
  totalCount: number;
  isFetching: boolean;
  onChange: (value: LandscapeFilterFormState) => void;
  onApply: () => void;
  onReset: () => void;
}

// Analytics filter panel. Shares the exact same query model as the patent
// landscape (via patentFilterModel) so a single filter state drives both the
// /api/analytics and /api/landscape requests. Datalist ids are prefixed with
// "analytics-" to avoid colliding with the landscape page's own datalists.
export function PatentFilterPanel({
  form,
  metadata,
  metadataError,
  metadataIsLoading,
  activeFilters,
  filteredCount,
  totalCount,
  isFetching,
  onChange,
  onApply,
  onReset,
}: PatentFilterPanelProps) {
  const publicationRange = metadata?.publication_year_range;
  const filingRange = metadata?.filing_year_range;
  const countryOptions = mergeOptions(metadata?.countries);
  const assigneeOptions = mergeOptions(
    countOptions(metadata?.top_assignees),
    metadata?.assignees,
  );
  const keywordOptions = mergeOptions(countOptions(metadata?.top_keywords));
  const applicationAreaOptions = mergeOptions(
    countOptions(metadata?.top_application_areas),
    metadata?.candidate_application_areas,
  );
  const classificationOptions = mergeOptions(
    countOptions(metadata?.top_classifications),
    metadata?.classifications,
  );
  const activeFilterChips = buildActiveFilterChips(activeFilters);
  const resetDisabled =
    isLandscapeFilterFormEmpty(form) &&
    !hasActiveLandscapeFilters(activeFilters);

  const updateField = <Key extends keyof LandscapeFilterFormState>(
    key: Key,
    value: LandscapeFilterFormState[Key],
  ) => {
    onChange({ ...form, [key]: value });
  };

  const toggleSource = (source: string, checked: boolean) => {
    const next = checked
      ? [...form.sources, source]
      : form.sources.filter((item) => item !== source);
    updateField(
      "sources",
      LANDSCAPE_SOURCES.filter((item) => next.includes(item)),
    );
  };

  return (
    <SectionCard
      title="Analytics filters"
      description="Shared corpus filter for charts and map metrics."
    >
      <form
        className="landscape-filter-panel"
        onSubmit={(event) => {
          event.preventDefault();
          onApply();
        }}
      >
        <div className="landscape-filter-panel__summary" aria-live="polite">
          <span>
            Showing <strong>{formatInteger(filteredCount)}</strong> of{" "}
            <strong>{formatInteger(totalCount)}</strong> patents.
          </span>
          {isFetching && (
            <span className="landscape-filter-panel__updating">
              <span className="loading-state__spinner" aria-hidden="true" />
              Updating charts...
            </span>
          )}
        </div>

        {metadataIsLoading && (
          <p className="filter-bar__hint">Loading filter metadata...</p>
        )}

        {metadataError !== null && metadataError !== undefined && (
          <Callout variant="warning" title="Filter options unavailable">
            <p>
              {metadataError instanceof ApiError
                ? metadataError.detail
                : String(metadataError)}
            </p>
          </Callout>
        )}

        <fieldset className="landscape-filter-panel__fieldset">
          <legend className="filter-field__label">Source authority</legend>
          <div className="landscape-filter-panel__sources">
            {LANDSCAPE_SOURCES.map((source) => (
              <label key={source} className="source-checkbox">
                <input
                  type="checkbox"
                  checked={form.sources.includes(source)}
                  onChange={(event) =>
                    toggleSource(source, event.target.checked)
                  }
                />
                <span>{source}</span>
                <span className="source-checkbox__count">
                  {countSuffix(metadata?.source_counts[source])}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="filter-bar__row">
          <label className="filter-field">
            <span className="filter-field__label">Publication from</span>
            <input
              type="number"
              value={form.publicationYearFrom}
              min={publicationRange?.min ?? undefined}
              max={publicationRange?.max ?? undefined}
              placeholder={yearPlaceholder(publicationRange?.min)}
              onChange={(event) =>
                updateField("publicationYearFrom", event.target.value)
              }
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Publication to</span>
            <input
              type="number"
              value={form.publicationYearTo}
              min={publicationRange?.min ?? undefined}
              max={publicationRange?.max ?? undefined}
              placeholder={yearPlaceholder(publicationRange?.max)}
              onChange={(event) =>
                updateField("publicationYearTo", event.target.value)
              }
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Filing from</span>
            <input
              type="number"
              value={form.filingYearFrom}
              min={filingRange?.min ?? undefined}
              max={filingRange?.max ?? undefined}
              placeholder={yearPlaceholder(filingRange?.min)}
              onChange={(event) =>
                updateField("filingYearFrom", event.target.value)
              }
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Filing to</span>
            <input
              type="number"
              value={form.filingYearTo}
              min={filingRange?.min ?? undefined}
              max={filingRange?.max ?? undefined}
              placeholder={yearPlaceholder(filingRange?.max)}
              onChange={(event) =>
                updateField("filingYearTo", event.target.value)
              }
            />
          </label>
        </div>

        <div className="filter-bar__row">
          <label className="filter-field">
            <span className="filter-field__label">Country</span>
            <input
              type="search"
              list="analytics-country-options"
              value={form.country}
              placeholder="All countries"
              autoComplete="off"
              onChange={(event) => updateField("country", event.target.value)}
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Application area</span>
            <input
              type="search"
              list="analytics-application-area-options"
              value={form.applicationArea}
              placeholder="All application areas"
              autoComplete="off"
              onChange={(event) =>
                updateField("applicationArea", event.target.value)
              }
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Assignee</span>
            <input
              type="text"
              list="analytics-assignee-options"
              value={form.assignee}
              placeholder="Assignee contains..."
              autoComplete="off"
              onChange={(event) => updateField("assignee", event.target.value)}
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Keyword</span>
            <input
              type="text"
              list="analytics-keyword-options"
              value={form.keyword}
              placeholder="Title, abstract, keyword..."
              autoComplete="off"
              onChange={(event) => updateField("keyword", event.target.value)}
            />
          </label>
          <label className="filter-field">
            <span className="filter-field__label">Classification</span>
            <input
              type="text"
              list="analytics-classification-options"
              value={form.classification}
              placeholder="IPC or CPC prefix..."
              autoComplete="off"
              onChange={(event) =>
                updateField("classification", event.target.value)
              }
            />
          </label>
        </div>

        <datalist id="analytics-country-options">
          {countryOptions.map((country) => (
            <option
              key={country}
              value={country}
              label={`${country}${countSuffix(metadata?.country_counts[country])}`}
            />
          ))}
        </datalist>
        <datalist id="analytics-assignee-options">
          {assigneeOptions.map((assignee) => (
            <option
              key={assignee}
              value={assignee}
              label={`${assignee}${countSuffix(metadata?.top_assignees[assignee])}`}
            />
          ))}
        </datalist>
        <datalist id="analytics-keyword-options">
          {keywordOptions.map((keyword) => (
            <option
              key={keyword}
              value={keyword}
              label={`${keyword}${countSuffix(metadata?.top_keywords[keyword])}`}
            />
          ))}
        </datalist>
        <datalist id="analytics-application-area-options">
          {applicationAreaOptions.map((area) => (
            <option
              key={area}
              value={area}
              label={`${area}${countSuffix(
                metadata?.top_application_areas[area],
              )}`}
            />
          ))}
        </datalist>
        <datalist id="analytics-classification-options">
          {classificationOptions.map((classification) => (
            <option
              key={classification}
              value={classification}
              label={`${classification}${countSuffix(
                metadata?.top_classifications[classification],
              )}`}
            />
          ))}
        </datalist>

        <div className="filter-bar__actions">
          <div className="landscape-filter-panel__chips" aria-live="polite">
            {activeFilterChips.length > 0 ? (
              activeFilterChips.map((chip) => (
                <span key={chip.key} className="chip chip--keyword">
                  {chip.label}
                </span>
              ))
            ) : (
              <span className="chip chip--muted">No corpus filters active</span>
            )}
          </div>
          <div className="landscape-filter-panel__actions">
            <button type="submit" className="button">
              Apply filters
            </button>
            <button
              type="button"
              className="button button--ghost"
              onClick={onReset}
              disabled={resetDisabled}
            >
              Reset filters
            </button>
          </div>
        </div>
      </form>
    </SectionCard>
  );
}
