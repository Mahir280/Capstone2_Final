import { useId } from "react";

import {
  GRAPH_PARAM_META,
  GRAPH_PARAM_ORDER,
  MAP_PRESETS,
  type GraphParamKey,
  type GraphParams,
  type GraphSelection,
  type PresetKey,
} from "./mapGraphPresets";

interface MapGraphControlsProps {
  selection: GraphSelection;
  params: GraphParams;
  onSelectPreset: (preset: PresetKey) => void;
  onChangeParam: (key: GraphParamKey, value: number) => void;
  densityMode: boolean;
  onToggleDensity: (value: boolean) => void;
  isFetching: boolean;
}

const PRESET_ORDER: PresetKey[] = ["tighter", "balanced", "broader"];

// Human-readable presets are the primary graph control, with the five raw
// parameters available in an Advanced expander. Density mode also stays local
// to the Map because it changes graph presentation rather than corpus filters.
export function MapGraphControls({
  selection,
  params,
  onSelectPreset,
  onChangeParam,
  densityMode,
  onToggleDensity,
  isFetching,
}: MapGraphControlsProps) {
  const groupName = useId();

  return (
    <div className="map-graph-controls" role="group" aria-label="Map grouping presets">
      <header className="map-graph-controls__intro">
        <span className="map-graph-controls__eyebrow">Grouping preset</span>
        <p className="map-graph-controls__body">
          Link strength preset. Corpus filters stay unchanged.
        </p>
      </header>

      <div
        className="map-graph-controls__presets"
        role="radiogroup"
        aria-label="Grouping preset"
      >
        {PRESET_ORDER.map((key) => {
          const def = MAP_PRESETS[key];
          const active = selection === key;
          return (
            <button
              key={key}
              type="button"
              role="radio"
              aria-checked={active}
              className={`map-preset${active ? " map-preset--active" : ""}`}
              onClick={() => onSelectPreset(key)}
              title={def.description}
            >
              <span className="map-preset__label">{def.label}</span>
              <span className="map-preset__desc">{def.description}</span>
            </button>
          );
        })}
      </div>

      {selection === "custom" && (
        <p className="map-graph-controls__custom" role="status">
          Custom grouping — raw values edited below.
        </p>
      )}

      <label className="map-graph-controls__toggle">
        <input
          type="checkbox"
          checked={densityMode}
          onChange={(event) => onToggleDensity(event.target.checked)}
        />
        <span className="map-graph-controls__toggle-text">
          <span className="map-graph-controls__toggle-title">Density mode</span>
          <span className="map-graph-controls__toggle-hint">
            Show crowded groups with larger nodes and halos.
          </span>
        </span>
      </label>

      <details className="map-graph-controls__advanced">
        <summary>Advanced graph controls</summary>
        <p className="map-graph-controls__advanced-note">
          Raw map parameters. Editing any value creates a Custom preset.
        </p>
        <div className="map-graph-controls__advanced-grid">
          {GRAPH_PARAM_ORDER.map((key) => {
            const meta = GRAPH_PARAM_META[key];
            const inputId = `${groupName}-${key}`;
            return (
              <div className="map-graph-controls__field" key={key}>
                <label className="map-graph-controls__field-label" htmlFor={inputId}>
                  {meta.label}
                </label>
                <input
                  id={inputId}
                  type="number"
                  className="map-graph-controls__field-input"
                  min={meta.min}
                  max={meta.max}
                  step={meta.step}
                  value={params[key]}
                  onChange={(event) => {
                    const next = Number(event.target.value);
                    if (Number.isNaN(next)) return;
                    const clamped = Math.min(meta.max, Math.max(meta.min, next));
                    onChangeParam(key, clamped);
                  }}
                />
                <span className="map-graph-controls__field-hint">{meta.hint}</span>
              </div>
            );
          })}
        </div>
      </details>

      {isFetching && (
        <p className="map-graph-controls__updating" role="status">
          <span className="loading-state__spinner" aria-hidden="true" />
          Rebuilding map…
        </p>
      )}
    </div>
  );
}
