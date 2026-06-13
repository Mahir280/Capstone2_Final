import { Badge } from "../common/Badge";
import { SectionCard } from "../common/SectionCard";
import { formatInteger } from "../filters/patentFilterModel";
import { colorForGroup } from "./LandscapeMiniGraph";
import {
  GROUP_DENSITY_BADGE,
  type GroupDensityModel,
} from "./groupDensitySignal";
import type { OverviewWhiteSpace } from "../opportunity/buildOverviewWhiteSpace";
import type { LandscapeTechnologyGroup } from "../../types/landscape";

// Keep this caveat consistent anywhere white-space signals are presented.
export const WHITE_SPACE_CAVEAT =
  "Exploratory signal, not a market or legal guarantee.";

interface MapWhiteSpacePanelProps {
  whiteSpace: OverviewWhiteSpace;
  groups: LandscapeTechnologyGroup[];
  density: GroupDensityModel;
  densityMode: boolean;
  appliedArea: string | undefined;
  onApplyArea: (area: string) => void;
}

// The Map's white-space panel reuses the same low-density logic as Overview,
// surfaces Crowded / Sparse badges from patent counts, explains the signals in
// a legend, and carries the interpretation caveat. Selecting an underexplored
// area applies its application-area facet to the shared filter state.
export function MapWhiteSpacePanel({
  whiteSpace,
  groups,
  density,
  densityMode,
  appliedArea,
  onApplyArea,
}: MapWhiteSpacePanelProps) {
  const sortedGroups = [...groups].sort(
    (a, b) => b.patent_count - a.patent_count,
  );
  const recentNote =
    whiteSpace.recentShare !== null && whiteSpace.recentWindow !== null
      ? `${Math.round(whiteSpace.recentShare * 100)}% of records are from ${whiteSpace.recentWindow.from}–${whiteSpace.recentWindow.to}; thin areas may be early.`
      : null;

  return (
    <SectionCard
      title="White space & density"
      description={WHITE_SPACE_CAVEAT}
    >
      <div className="map-whitespace">
        <Legend densityMode={densityMode} />

        <div className="map-whitespace__section">
          <h3 className="map-whitespace__heading">
            Crowded vs. sparse technology groups
          </h3>
          {sortedGroups.length === 0 ? (
            <p className="card__muted">
              No technology groups are in view for the current filter.
            </p>
          ) : (
            <ul className="map-whitespace__groups">
              {sortedGroups.map((group) => {
                const signal = density.byGroupId.get(group.technology_group_id);
                const badge = signal
                  ? GROUP_DENSITY_BADGE[signal.tier]
                  : null;
                return (
                  <li
                    key={group.technology_group_id}
                    className="map-whitespace__group"
                  >
                    <span
                      className="map-whitespace__swatch"
                      style={{
                        background: colorForGroup(group.technology_group_id),
                      }}
                      aria-hidden="true"
                    />
                    <span className="map-whitespace__group-label">
                      {group.group_label || group.technology_group}
                    </span>
                    <span className="map-whitespace__group-count">
                      {formatInteger(group.patent_count)}{" "}
                      {group.patent_count === 1 ? "patent" : "patents"}
                    </span>
                    {badge && (
                      <Badge variant={badge.variant}>{badge.label}</Badge>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="map-whitespace__section">
          <h3 className="map-whitespace__heading">
            Underexplored application areas
          </h3>
          {whiteSpace.areas.length === 0 ? (
            <p className="card__muted">
              {whiteSpace.totalAreas === 0
                ? "No candidate application areas are available for these records."
                : "No clearly underexplored application areas for the active filter."}
            </p>
          ) : (
            <>
              <p className="map-whitespace__context">
                Median area: {whiteSpace.medianCount.toFixed(1)} records.
                Largest: {formatInteger(whiteSpace.maxCount)}.
                {recentNote ? ` ${recentNote}` : ""}
              </p>
              <ul className="map-whitespace__areas">
                {whiteSpace.areas.map((area) => {
                  const isApplied = appliedArea === area.name;
                  return (
                    <li key={area.name}>
                      <button
                        type="button"
                        className={`map-whitespace__area${
                          isApplied ? " map-whitespace__area--applied" : ""
                        }`}
                        onClick={() => onApplyArea(area.name)}
                        aria-pressed={isApplied}
                      >
                        <span className="map-whitespace__area-name">
                          {area.name}
                        </span>
                        <span className="map-whitespace__area-meta">
                          <span className="map-whitespace__area-count">
                            {formatInteger(area.count)}{" "}
                            {area.count === 1 ? "record" : "records"}
                          </span>
                          <span
                            className="map-whitespace__area-go"
                            aria-hidden="true"
                          >
                            {isApplied ? "Filtered ✓" : "Filter Map →"}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </div>
      </div>
    </SectionCard>
  );
}

function Legend({ densityMode }: { densityMode: boolean }) {
  return (
    <div className="map-whitespace__legend" aria-label="Density and white-space legend">
      <span className="map-whitespace__legend-item">
        <span
          className="map-whitespace__legend-dot map-whitespace__legend-dot--crowded"
          aria-hidden="true"
        />
        Crowded group
      </span>
      <span className="map-whitespace__legend-item">
        <span
          className="map-whitespace__legend-dot map-whitespace__legend-dot--sparse"
          aria-hidden="true"
        />
        Sparse group
      </span>
      <span className="map-whitespace__legend-item">
        <span className="map-whitespace__legend-halo" aria-hidden="true" />
        Density mode {densityMode ? "on" : "off"}
      </span>
    </div>
  );
}
