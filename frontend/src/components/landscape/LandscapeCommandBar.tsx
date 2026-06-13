import { Link } from "react-router-dom";

import { encodeAnalysisId } from "../../api/patents";
import { Badge } from "../common/Badge";
import { StatTile } from "../common/StatTile";
import type { LandscapeNode } from "../../types/landscape";

interface LandscapeCommandBarProps {
  totalPatents: number;
  visiblePatents: number;
  totalEdges: number;
  visibleEdges: number;
  totalGroups: number;
  activeGroupsCount: number;
  threshold: number;
  isFocused: boolean;
  focusedId: string | null;
  focusedNode: LandscapeNode | null;
  selectedNode: LandscapeNode | null;
  onClearFocus: () => void;
  onClearSelection: () => void;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat().format(value);
}

export function LandscapeCommandBar({
  totalPatents,
  visiblePatents,
  totalEdges,
  visibleEdges,
  totalGroups,
  activeGroupsCount,
  threshold,
  isFocused,
  focusedId,
  focusedNode,
  selectedNode,
  onClearFocus,
  onClearSelection,
}: LandscapeCommandBarProps) {
  const focusLabel = focusedNode
    ? focusedNode.title || focusedNode.patent_id
    : focusedId;

  return (
    <section
      className="landscape-command-bar"
      role="region"
      aria-label="Map workspace status"
    >
      <div className="landscape-command-bar__stats">
        <StatTile
          classNamePrefix="landscape-command-bar"
          label="Patents in view"
          value={formatNumber(visiblePatents)}
          subValue={`/ ${formatNumber(totalPatents)} loaded`}
          primary
        />
        <StatTile
          classNamePrefix="landscape-command-bar"
          label="Visible relationships"
          value={formatNumber(visibleEdges)}
          subValue={`/ ${formatNumber(totalEdges)} total`}
        />
        <StatTile
          classNamePrefix="landscape-command-bar"
          label="Active technology groups"
          value={formatNumber(activeGroupsCount)}
          subValue={`/ ${formatNumber(totalGroups)}`}
        />
        <StatTile
          classNamePrefix="landscape-command-bar"
          label="Relationship threshold"
          value={`≥ ${threshold.toFixed(3)}`}
          subValue="similarity"
        />
      </div>

      <div className="landscape-command-bar__state">
        <div className="landscape-command-bar__chips">
          {isFocused ? (
            <Badge variant="accent" withDot>
              Focused neighborhood
            </Badge>
          ) : (
            <Badge variant="primary" withDot>
              Full map workspace
            </Badge>
          )}
          {selectedNode && (
            <Badge variant="neutral">
              Selected: {selectedNode.title || selectedNode.patent_id}
            </Badge>
          )}
        </div>

        {isFocused && focusedId && (
          <div className="landscape-command-bar__focus">
            <span className="landscape-command-bar__focus-label">
              Focused on
            </span>
            <span className="landscape-command-bar__focus-title" title={focusedId}>
              {focusLabel}
            </span>
            <div className="landscape-command-bar__focus-actions">
              <Link
                className="link-button"
                to={`/patents/${encodeAnalysisId(focusedId)}`}
              >
                Open dossier →
              </Link>
              <button
                type="button"
                className="button button--ghost button--sm"
                onClick={onClearFocus}
              >
                Clear focus
              </button>
            </div>
          </div>
        )}

        {!isFocused && selectedNode && (
          <div className="landscape-command-bar__focus">
            <span className="landscape-command-bar__focus-label">
              Selected patent
            </span>
            <span
              className="landscape-command-bar__focus-title"
              title={selectedNode.patent_id}
            >
              {selectedNode.title || selectedNode.patent_id}
            </span>
            <div className="landscape-command-bar__focus-actions">
              <button
                type="button"
                className="button button--ghost button--sm"
                onClick={onClearSelection}
              >
                Clear selection
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
