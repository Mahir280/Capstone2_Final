import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { ApiError } from "../api/client";
import { getFocusedLandscape } from "../api/landscape";
import {
  encodeAnalysisId,
  getPatentProfile,
  getRelatedPatents,
} from "../api/patents";
import { Badge } from "../components/common/Badge";
import { Callout } from "../components/common/Callout";
import { DatasetWarningCallout } from "../components/common/DatasetWarningCallout";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { MetricCard } from "../components/common/MetricCard";
import { PageHeader } from "../components/common/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import { LandscapeMiniGraph } from "../components/landscape/LandscapeMiniGraph";
import { CandidateApplicationAreasPanel } from "../components/patents/CandidateApplicationAreasPanel";
import { KeywordChips } from "../components/patents/KeywordChips";
import { PatentComparisonPanel } from "../components/patents/PatentComparisonPanel";
import { RelatedPatentDossierCard } from "../components/patents/RelatedPatentDossierCard";
import type { PatentProfile, RelatedPatent } from "../types/patents";
import type {
  LandscapeEdge,
  LandscapeNode,
  LandscapeResponse,
} from "../types/landscape";

const SAFETY_NOTE =
  "Review aid only. Similarity and overlap signals are not claim-scope analysis or legal advice.";

function describeNumber(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function evidenceVariant(
  level: string,
): "success" | "primary" | "warning" | "neutral" {
  const normalized = level.toLowerCase();
  if (normalized.includes("strong") || normalized.includes("high")) return "success";
  if (normalized.includes("moderate") || normalized.includes("medium")) return "primary";
  if (normalized.includes("weak") || normalized.includes("low")) return "warning";
  return "neutral";
}

function strengthVariant(
  label: string,
): "success" | "primary" | "warning" | "neutral" {
  const normalized = label.toLowerCase();
  if (normalized.includes("strong")) return "success";
  if (normalized.includes("moderate")) return "primary";
  if (normalized.includes("weak")) return "warning";
  return "neutral";
}

function overlapVariant(
  label: string,
): "success" | "primary" | "warning" | "neutral" | "accent" {
  const normalized = label.toLowerCase();
  if (normalized.includes("strong") || normalized.includes("high")) return "success";
  if (normalized.includes("moderate") || normalized.includes("medium")) return "primary";
  if (normalized.includes("weak") || normalized.includes("low")) return "warning";
  return "accent";
}

export function PatentProfilePage() {
  const params = useParams<{ analysisId: string }>();
  const analysisId = useMemo(() => {
    const raw = params.analysisId ?? "";
    try {
      return decodeURIComponent(raw);
    } catch {
      return raw;
    }
  }, [params.analysisId]);

  const profileQuery = useQuery({
    queryKey: ["patent-profile", analysisId],
    queryFn: ({ signal }) => getPatentProfile(analysisId, signal),
    enabled: analysisId.length > 0,
  });

  const profile = profileQuery.data;
  const relatedFallbackQuery = useQuery({
    queryKey: ["patent-related", analysisId],
    queryFn: ({ signal }) => getRelatedPatents(analysisId, signal),
    enabled: Boolean(
      profile && profile.related_patents.length === 0 && analysisId.length > 0,
    ),
  });

  if (!analysisId) {
    return (
      <section>
        <PageHeader
          eyebrow="Explore"
          title="Patent Dossier"
          breadcrumb={<Link to="/search">← Back to Search</Link>}
        />
        <ErrorState
          title="Missing patent identifier"
          message="No analysis_id was provided in the URL. Open a patent from Search."
        />
      </section>
    );
  }

  if (profileQuery.isPending) {
    return (
      <section>
        <PageHeader
          eyebrow="Explore"
          title="Patent Dossier"
          breadcrumb={<Link to="/search">← Back to Search</Link>}
        />
        <LoadingState message="Loading patent dossier..." />
      </section>
    );
  }

  if (profileQuery.isError || !profile) {
    const err = profileQuery.error;
    const isNotFound = err instanceof ApiError && err.status === 404;
    return (
      <section>
        <PageHeader
          eyebrow="Explore"
          title="Patent Dossier"
          breadcrumb={<Link to="/search">← Back to Search</Link>}
        />
        <ErrorState
          title={isNotFound ? "Patent not found" : "Could not load patent"}
          message={
            err instanceof ApiError
              ? err.detail
              : err
              ? String(err)
              : "Unknown error"
          }
          hint={
            isNotFound
              ? `No loaded patent matches analysis_id "${analysisId}".`
              : "Make sure the FastAPI backend is running at the configured VITE_API_BASE_URL."
          }
        />
      </section>
    );
  }

  const relatedPatents =
    profile.related_patents.length > 0
      ? profile.related_patents
      : relatedFallbackQuery.data?.related_patents ?? [];

  return (
    <ProfileContent
      profile={profile}
      related={relatedPatents}
      isFallbackLoading={
        relatedFallbackQuery.isPending &&
        profile.related_patents.length === 0
      }
      fallbackError={relatedFallbackQuery.error}
    />
  );
}

interface ProfileContentProps {
  profile: PatentProfile;
  related: RelatedPatent[];
  isFallbackLoading: boolean;
  fallbackError: unknown;
}

function ProfileContent({
  profile,
  related,
  isFallbackLoading,
  fallbackError,
}: ProfileContentProps) {
  const navigate = useNavigate();
  const summary = useMemo(
    () => summarizeRelationships(related, profile),
    [related, profile],
  );
  const [selectedNeighborhoodId, setSelectedNeighborhoodId] = useState<
    string | null
  >(profile.analysis_id);
  const [hoveredNeighborhoodId, setHoveredNeighborhoodId] = useState<
    string | null
  >(null);
  const [comparedAnalysisId, setComparedAnalysisId] = useState<string | null>(
    null,
  );

  useEffect(() => {
    setSelectedNeighborhoodId(profile.analysis_id);
    setHoveredNeighborhoodId(null);
    setComparedAnalysisId(null);
  }, [profile.analysis_id]);

  const handleCompareRelated = (analysisId: string) => {
    setComparedAnalysisId((prev) => {
      const next = prev === analysisId ? null : analysisId;
      if (next && typeof window !== "undefined") {
        window.requestAnimationFrame(() => {
          const panel = document.getElementById("related-patent-comparison");
          if (panel) {
            panel.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        });
      }
      return next;
    });
  };

  const focusedLandscapeQuery = useQuery({
    queryKey: ["dossier-neighborhood", profile.analysis_id],
    queryFn: ({ signal }) =>
      getFocusedLandscape(profile.analysis_id, { max_edges: 40 }, signal),
    enabled: profile.analysis_id.length > 0,
  });

  return (
    <section>
      <DossierHero profile={profile} relationshipCount={summary.count} />

      <DatasetWarningCallout warnings={profile.warnings} />

      <RelationshipIntelligenceSection
        profile={profile}
        related={related}
        summary={summary}
        isFallbackLoading={isFallbackLoading}
      />

      <RelationshipNeighborhoodPanel
        profile={profile}
        related={related}
        data={focusedLandscapeQuery.data}
        isLoading={focusedLandscapeQuery.isPending}
        error={focusedLandscapeQuery.error}
        selectedId={selectedNeighborhoodId}
        hoveredId={hoveredNeighborhoodId}
        onSelectNode={setSelectedNeighborhoodId}
        onHoverNode={setHoveredNeighborhoodId}
        onOpenPatent={(analysisId) =>
          navigate(`/patents/${encodeAnalysisId(analysisId)}`)
        }
      />

      {profile.candidate_application_areas.length > 0 && (
        <CandidateApplicationAreasPanel
          areas={profile.candidate_application_areas}
          related={related}
        />
      )}

      <RelatedPatentsSection
        profile={profile}
        related={related}
        isFallbackLoading={isFallbackLoading}
        fallbackError={fallbackError}
        comparedAnalysisId={comparedAnalysisId}
        onCompare={handleCompareRelated}
        onCloseComparison={() => setComparedAnalysisId(null)}
      />

      <TechnicalEvidencePanel profile={profile} />
    </section>
  );
}

// ---- Relationship intelligence summary -------------------------------------

interface RelationshipSummary {
  count: number;
  strongest: RelatedPatent | null;
  sameGroupCount: number;
  highestOverlap: RelatedPatent | null;
  strengthDistribution: Array<{ label: string; count: number }>;
  overlapDistribution: Array<{ label: string; count: number }>;
  mainRelatedGroup: { name: string; count: number } | null;
  crossAuthorityCount: number;
}

function summarizeRelationships(
  related: RelatedPatent[],
  profile: PatentProfile,
): RelationshipSummary {
  if (related.length === 0) {
    return {
      count: 0,
      strongest: null,
      sameGroupCount: 0,
      highestOverlap: null,
      strengthDistribution: [],
      overlapDistribution: [],
      mainRelatedGroup: null,
      crossAuthorityCount: 0,
    };
  }
  let strongest = related[0];
  let highestOverlap = related[0];
  let sameGroupCount = 0;
  let crossAuthorityCount = 0;
  const strengthCounts = new Map<string, number>();
  const overlapCounts = new Map<string, number>();
  const groupCounts = new Map<string, number>();
  const profileAuthority = profile.source_authority || profile.source;
  for (const rel of related) {
    if (rel.similarity_score > strongest.similarity_score) strongest = rel;
    if (rel.overlap_score > highestOverlap.overlap_score) highestOverlap = rel;
    if (rel.same_technology_group) sameGroupCount += 1;
    if (rel.relationship_strength) {
      strengthCounts.set(
        rel.relationship_strength,
        (strengthCounts.get(rel.relationship_strength) ?? 0) + 1,
      );
    }
    if (rel.overlap_signal) {
      overlapCounts.set(
        rel.overlap_signal,
        (overlapCounts.get(rel.overlap_signal) ?? 0) + 1,
      );
    }
    const group = rel.target_technology_group || rel.source_technology_group;
    if (group) {
      groupCounts.set(group, (groupCounts.get(group) ?? 0) + 1);
    }
    const relAuthority = rel.source_authority || rel.source;
    if (
      profileAuthority &&
      relAuthority &&
      relAuthority.toLowerCase() !== profileAuthority.toLowerCase()
    ) {
      crossAuthorityCount += 1;
    }
  }
  const strengthDistribution = Array.from(strengthCounts.entries())
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count);
  const overlapDistribution = Array.from(overlapCounts.entries())
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count);
  let mainRelatedGroup: { name: string; count: number } | null = null;
  for (const [name, count] of groupCounts.entries()) {
    if (!mainRelatedGroup || count > mainRelatedGroup.count) {
      mainRelatedGroup = { name, count };
    }
  }
  return {
    count: related.length,
    strongest,
    sameGroupCount,
    highestOverlap,
    strengthDistribution,
    overlapDistribution,
    mainRelatedGroup,
    crossAuthorityCount,
  };
}

interface RelationshipIntelligenceSectionProps {
  profile: PatentProfile;
  related: RelatedPatent[];
  summary: RelationshipSummary;
  isFallbackLoading: boolean;
}

function RelationshipIntelligenceSection({
  profile,
  related,
  summary,
  isFallbackLoading,
}: RelationshipIntelligenceSectionProps) {
  const focusedLandscapeLink = `/map?focus=${encodeAnalysisId(
    profile.analysis_id,
  )}`;

  if (isFallbackLoading) {
    return (
      <SectionCard
        title="Relationship intelligence"
        description="Loading similarity signals for this patent..."
      >
        <LoadingState message="Loading relationship neighborhood..." />
      </SectionCard>
    );
  }

  if (related.length === 0) {
    return (
      <SectionCard
        title="Relationship intelligence"
        description="Similarity signals for this patent."
        actions={
          <Link className="link-button" to={focusedLandscapeLink}>
            View relationship neighborhood on Map →
          </Link>
        }
      >
        <Callout variant="neutral">
          <p style={{ margin: 0 }}>
            No related patents exceeded the current similarity threshold.
          </p>
        </Callout>
      </SectionCard>
    );
  }

  const strongest = summary.strongest;
  const highestOverlap = summary.highestOverlap;
  const sameGroupPercent =
    summary.count > 0
      ? Math.round((summary.sameGroupCount / summary.count) * 100)
      : 0;

  return (
    <SectionCard
      title="Relationship intelligence"
      description="Related patents, similarity signals, and overlap signals."
      actions={
        <Link className="link-button" to={focusedLandscapeLink}>
          View relationship neighborhood on Map →
        </Link>
      }
    >
      <div className="profile-intelligence">
        <div className="relationship-summary metric-grid">
          <MetricCard
            label="Related patents"
            value={summary.count}
            hint={
              summary.crossAuthorityCount > 0
                ? `${summary.crossAuthorityCount} cross-authority link${
                    summary.crossAuthorityCount === 1 ? "" : "s"
                  }`
                : "All from the same source authority"
            }
            variant="primary"
          />
          {strongest && (
            <MetricCard
              label="Strongest relationship"
              value={`${strongest.relationship_strength} (${describeNumber(
                strongest.similarity_score,
              )})`}
              hint={
                <>
                  {strongest.title || strongest.patent_id}
                  <br />
                  Cosine text similarity, scale 0–1.
                </>
              }
              variant="accent"
            />
          )}
          {summary.mainRelatedGroup && (
            <MetricCard
              label="Main related technology group"
              value={summary.mainRelatedGroup.name}
              hint={`${summary.mainRelatedGroup.count} of ${summary.count} share this group`}
            />
          )}
          {highestOverlap && (
            <MetricCard
              label="Strongest overlap signal"
              value={`${highestOverlap.overlap_signal} (${describeNumber(
                highestOverlap.overlap_score,
              )})`}
              hint={
                <>
                  {highestOverlap.title || highestOverlap.patent_id}
                  <br />
                  Overlap score, scale 0–100 (≥75 High, ≥50 Medium).
                </>
              }
              compact
            />
          )}
        </div>

        <div className="profile-intelligence__row">
          {summary.strengthDistribution.length > 0 && (
            <DistributionBlock
              label="Relationship strength distribution"
              entries={summary.strengthDistribution}
              total={summary.count}
              variantOf={strengthVariant}
            />
          )}
          {summary.overlapDistribution.length > 0 && (
            <DistributionBlock
              label="Overlap signal distribution"
              entries={summary.overlapDistribution}
              total={summary.count}
              variantOf={overlapVariant}
            />
          )}
          {summary.count > 0 && (
            <div className="profile-intelligence__neighborhood">
              <span className="profile-intelligence__label">
                Technology group fit
              </span>
              <p className="profile-intelligence__body">
                {summary.sameGroupCount > 0 ? (
                  <>
                    <strong>{summary.sameGroupCount}</strong> of{" "}
                    <strong>{summary.count}</strong> related patents (
                    {sameGroupPercent}%) sit in the same technology group as
                    this one — a tight, in-group relationship neighborhood.
                  </>
                ) : (
                  <>
                    None of the related patents share this patent's technology
                    group; the relationship neighborhood spans multiple
                    technology groups.
                  </>
                )}
              </p>
            </div>
          )}
        </div>
      </div>
    </SectionCard>
  );
}

interface DistributionEntry {
  label: string;
  count: number;
}

function DistributionBlock({
  label,
  entries,
  total,
  variantOf,
}: {
  label: string;
  entries: DistributionEntry[];
  total: number;
  variantOf: (label: string) => "success" | "primary" | "warning" | "neutral" | "accent";
}) {
  return (
    <div className="profile-intelligence__distribution">
      <span className="profile-intelligence__label">{label}</span>
      <ul className="distribution-bars">
        {entries.map((entry) => {
          const pct = total > 0 ? Math.round((entry.count / total) * 100) : 0;
          const variant = variantOf(entry.label);
          return (
            <li key={entry.label} className="distribution-bars__row">
              <span className="distribution-bars__head">
                <Badge variant={variant}>{entry.label}</Badge>
                <span className="distribution-bars__count">
                  {entry.count} ({pct}%)
                </span>
              </span>
              <span
                className={`distribution-bars__track distribution-bars__track--${variant}`}
                aria-hidden="true"
              >
                <span
                  className="distribution-bars__fill"
                  style={{ width: `${pct}%` }}
                />
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ---- Dossier overview, neighborhood, application areas, related patents ----

function DossierHero({
  profile,
  relationshipCount,
}: {
  profile: PatentProfile;
  relationshipCount: number;
}) {
  const authority = profile.source_authority || profile.source || "—";
  const overview = profile.plain_language_summary || profile.abstract;
  const publication = profile.publication_date || profile.year || "—";
  const facts = [
    {
      label: "Patent ID",
      value: <span className="patent-card__id">{profile.patent_id}</span>,
    },
    {
      label: "Analysis ID",
      value: <span className="profile-hero__analysis-id">{profile.analysis_id}</span>,
    },
    { label: "Source authority", value: authority },
    { label: "Assignee / applicant", value: profile.assignee || "—" },
    { label: "Publication", value: publication },
    { label: "Jurisdiction", value: profile.country || "—" },
  ];

  return (
    <div className="profile-hero">
      <div className="profile-hero__breadcrumb">
        <Link to="/search">← Back to Search</Link>
      </div>
      <div className="profile-hero__layout">
        <div className="profile-hero__main">
          <div className="profile-hero__eyebrow">Patent Dossier</div>
          <h1 className="profile-hero__title">
            {profile.title || profile.patent_id}
          </h1>
          <p className="profile-hero__description">
            A research dossier for this patent's identity, technical context,
            relationship neighborhood, candidate application areas, and related
            records in the current corpus.
          </p>
          {overview && (
            <div className="profile-hero__abstract">
              <span className="profile-hero__section-label">
                Short overview
              </span>
              <p>{overview}</p>
            </div>
          )}
          <div className="chip-row profile-hero__chips">
            {authority !== "—" && (
              <span className="chip chip--authority">{authority}</span>
            )}
            {profile.import_method && (
              <Badge variant="neutral">Import: {profile.import_method}</Badge>
            )}
            {relationshipCount > 0 && (
              <Badge variant="primary" withDot>
                {relationshipCount} related patent
                {relationshipCount === 1 ? "" : "s"}
              </Badge>
            )}
            <Badge variant="accent">Optimized grouping context</Badge>
          </div>
        </div>

        <aside className="profile-hero__side" aria-label="Patent overview">
          <div className="profile-hero__facts">
            {facts.map((fact) => (
              <div key={fact.label} className="profile-hero__fact">
                <span className="profile-hero__fact-label">{fact.label}</span>
                <span className="profile-hero__fact-value">{fact.value}</span>
              </div>
            ))}
          </div>
          <div className="profile-hero__corpus">
            <span className="profile-hero__section-label">Corpus context</span>
            <p>
              Loaded corpus record with source authority preserved.
            </p>
            {profile.source_url && (
              <a
                className="link-button"
                href={profile.source_url}
                target="_blank"
                rel="noreferrer noopener"
              >
                Open source page ↗
              </a>
            )}
          </div>
        </aside>
      </div>

      <div className="profile-hero__safety" role="note">
        {SAFETY_NOTE}
      </div>
    </div>
  );
}

interface RelationshipNeighborhoodPanelProps {
  profile: PatentProfile;
  related: RelatedPatent[];
  data: LandscapeResponse | undefined;
  isLoading: boolean;
  error: unknown;
  selectedId: string | null;
  hoveredId: string | null;
  onSelectNode: (analysisId: string | null) => void;
  onHoverNode: (analysisId: string | null) => void;
  onOpenPatent: (analysisId: string) => void;
}

function RelationshipNeighborhoodPanel({
  profile,
  related,
  data,
  isLoading,
  error,
  selectedId,
  hoveredId,
  onSelectNode,
  onHoverNode,
  onOpenPatent,
}: RelationshipNeighborhoodPanelProps) {
  const focusedLandscapeLink = `/map?focus=${encodeAnalysisId(
    profile.analysis_id,
  )}`;

  if (isLoading) {
    return (
      <SectionCard
        title="Relationship neighborhood"
        description="Loading focused neighborhood."
      >
        <LoadingState message="Loading relationship neighborhood..." />
      </SectionCard>
    );
  }

  if (error || !data) {
    return (
      <SectionCard
        title="Relationship neighborhood"
        description="Focused map data unavailable."
        actions={
          <Link className="link-button" to={focusedLandscapeLink}>
            View neighborhood on Map →
          </Link>
        }
      >
        <Callout variant="neutral">
          <p style={{ margin: 0 }}>
            Related-patent evidence below is still available.
          </p>
        </Callout>
      </SectionCard>
    );
  }

  if (data.nodes.length === 0) {
    return (
      <SectionCard
        title="Relationship neighborhood"
        description="Focused map of nearby related records."
        actions={
          <Link className="link-button" to={focusedLandscapeLink}>
            View neighborhood on Map →
          </Link>
        }
      >
        <Callout variant="neutral">
          <p style={{ margin: 0 }}>
            No focused map nodes are available for this patent yet.
          </p>
        </Callout>
      </SectionCard>
    );
  }

  const nodeIndex = buildLandscapeNodeIndex(data.nodes);
  const graphSelectedId =
    selectedId && nodeIndex.has(selectedId) ? selectedId : profile.analysis_id;
  const selectedNode =
    nodeIndex.get(graphSelectedId) ?? nodeIndex.get(profile.analysis_id) ?? null;
  const selectedEdges = selectedNode
    ? edgesForNode(data.edges, selectedNode.analysis_id)
    : [];

  return (
    <SectionCard
      title="Relationship neighborhood"
      description="Focused mini-map of this patent and related patents."
      actions={
        <Link className="link-button" to={focusedLandscapeLink}>
          View neighborhood on Map →
        </Link>
      }
    >
      <div className="relationship-neighborhood">
        <div className="relationship-neighborhood__map">
          <LandscapeMiniGraph
            data={data}
            height={320}
            selectedId={graphSelectedId}
            hoveredId={hoveredId}
            onHoverNode={onHoverNode}
            onSelectNode={(analysisId) =>
              onSelectNode(analysisId ?? profile.analysis_id)
            }
            onOpenNode={onOpenPatent}
            className="relationship-neighborhood__mini-graph"
            ariaLabel="Focused relationship-neighborhood mini graph"
            caption={
              <>
                Selected patents show source, group, and neighborhood links.
              </>
            }
          />
        </div>
        <NeighborhoodSelectionPanel
          currentAnalysisId={profile.analysis_id}
          selectedNode={selectedNode}
          selectedEdges={selectedEdges}
          nodeIndex={nodeIndex}
          relatedCount={related.length}
          onOpenPatent={onOpenPatent}
        />
      </div>
    </SectionCard>
  );
}

function buildLandscapeNodeIndex(
  nodes: LandscapeNode[],
): Map<string, LandscapeNode> {
  const map = new Map<string, LandscapeNode>();
  for (const node of nodes) map.set(node.analysis_id, node);
  return map;
}

function edgesForNode(edges: LandscapeEdge[], analysisId: string): LandscapeEdge[] {
  return [...edges]
    .filter(
      (edge) =>
        edge.source_analysis_id === analysisId ||
        edge.target_analysis_id === analysisId,
    )
    .sort((a, b) => b.similarity_score - a.similarity_score);
}

function otherNodeId(edge: LandscapeEdge, analysisId: string): string {
  return edge.source_analysis_id === analysisId
    ? edge.target_analysis_id
    : edge.source_analysis_id;
}

function NeighborhoodSelectionPanel({
  currentAnalysisId,
  selectedNode,
  selectedEdges,
  nodeIndex,
  relatedCount,
  onOpenPatent,
}: {
  currentAnalysisId: string;
  selectedNode: LandscapeNode | null;
  selectedEdges: LandscapeEdge[];
  nodeIndex: Map<string, LandscapeNode>;
  relatedCount: number;
  onOpenPatent: (analysisId: string) => void;
}) {
  if (!selectedNode) {
    return (
      <aside className="relationship-neighborhood__panel">
        <p className="card__muted">
          Select a node in the relationship neighborhood to inspect its context.
        </p>
      </aside>
    );
  }

  const isCurrent = selectedNode.analysis_id === currentAnalysisId;
  const strongest = selectedEdges[0] ?? null;
  const strongestNeighbor = strongest
    ? nodeIndex.get(otherNodeId(strongest, selectedNode.analysis_id))
    : null;

  return (
    <aside className="relationship-neighborhood__panel">
      <header className="relationship-neighborhood__panel-head">
        <div>
          <span className="profile-intelligence__label">
            {isCurrent ? "Current patent" : "Selected related patent"}
          </span>
          <h3 className="relationship-neighborhood__title">
            {selectedNode.title || selectedNode.patent_id}
          </h3>
          <span className="relationship-neighborhood__sub">
            {selectedNode.patent_id}
          </span>
        </div>
        {isCurrent ? (
          <Badge variant="primary" withDot>
            Active
          </Badge>
        ) : (
          <button
            type="button"
            className="button button--ghost button--sm"
            onClick={() => onOpenPatent(selectedNode.analysis_id)}
          >
            Open dossier →
          </button>
        )}
      </header>

      <dl className="relationship-neighborhood__facts">
        <div>
          <dt>Source authority</dt>
          <dd>{selectedNode.source_authority || selectedNode.source || "—"}</dd>
        </div>
        <div>
          <dt>Technology group</dt>
          <dd>{selectedNode.technology_group || "—"}</dd>
        </div>
        <div>
          <dt>Neighborhood links</dt>
          <dd>
            {selectedEdges.length}
            {isCurrent && relatedCount > 0 && (
              <span className="relationship-neighborhood__muted">
                {" "}
                / {relatedCount} dossier relationships
              </span>
            )}
          </dd>
        </div>
        <div>
          <dt>Strongest relationship</dt>
          <dd>
            {strongest
              ? `${strongest.relationship_strength} (${describeNumber(
                  strongest.similarity_score,
                )})`
              : "—"}
          </dd>
        </div>
      </dl>

      {strongestNeighbor && (
        <div className="relationship-neighborhood__strongest">
          <span className="profile-intelligence__label">
            Strongest neighbor
          </span>
          <span>{strongestNeighbor.title || strongestNeighbor.patent_id}</span>
        </div>
      )}

      {selectedNode.candidate_application_areas.length > 0 && (
        <div className="relationship-neighborhood__areas">
          <span className="profile-intelligence__label">
            Candidate application areas
          </span>
          <div className="chip-row">
            {selectedNode.candidate_application_areas.slice(0, 5).map((area) => (
              <span key={area} className="chip chip--area">
                {area}
              </span>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}

type RelatedSortMode = "default" | "strength" | "overlap" | "sameGroup";

interface RelatedPatentsSectionProps {
  profile: PatentProfile;
  related: RelatedPatent[];
  isFallbackLoading: boolean;
  fallbackError: unknown;
  comparedAnalysisId: string | null;
  onCompare: (analysisId: string) => void;
  onCloseComparison: () => void;
}

function RelatedPatentsSection({
  profile,
  related,
  isFallbackLoading,
  fallbackError,
  comparedAnalysisId,
  onCompare,
  onCloseComparison,
}: RelatedPatentsSectionProps) {
  const [sortMode, setSortMode] = useState<RelatedSortMode>("default");

  const sortedRelated = useMemo(() => {
    if (sortMode === "default") return related;
    const copy = [...related];
    if (sortMode === "strength") {
      copy.sort((a, b) => b.similarity_score - a.similarity_score);
    } else if (sortMode === "overlap") {
      copy.sort((a, b) => b.overlap_score - a.overlap_score);
    } else if (sortMode === "sameGroup") {
      copy.sort((a, b) => {
        const groupDiff = Number(b.same_technology_group) - Number(a.same_technology_group);
        if (groupDiff !== 0) return groupDiff;
        return b.similarity_score - a.similarity_score;
      });
    }
    return copy;
  }, [related, sortMode]);

  const comparedRelated = useMemo(() => {
    if (!comparedAnalysisId) return null;
    return related.find((r) => r.analysis_id === comparedAnalysisId) ?? null;
  }, [related, comparedAnalysisId]);

  if (isFallbackLoading) {
    return (
      <SectionCard title="Related patents">
        <LoadingState message="Loading related patents..." />
      </SectionCard>
    );
  }

  if (related.length === 0) {
    return (
      <SectionCard title="Related patents">
        <p className="card__muted">
          {fallbackError
            ? "Related patents could not be loaded."
            : "No similarity-based overlap signal exceeded the current threshold."}
        </p>
      </SectionCard>
    );
  }

  const sameGroupCount = related.reduce(
    (acc, r) => acc + (r.same_technology_group ? 1 : 0),
    0,
  );

  return (
    <SectionCard
      title="Related patents"
      description="Similarity signals and review aids."
    >
      <div className="related-toolbar" role="toolbar" aria-label="Related patents controls">
        <div className="related-toolbar__summary">
          <strong>{related.length}</strong> related patent
          {related.length === 1 ? "" : "s"} in this relationship neighborhood
          {sameGroupCount > 0 && (
            <span className="related-toolbar__hint">
              {" "}
              · {sameGroupCount} in the same technology group
            </span>
          )}
        </div>
        <label className="related-toolbar__sort">
          <span className="related-toolbar__sort-label">Sort by</span>
          <select
            value={sortMode}
            onChange={(event) =>
              setSortMode(event.target.value as RelatedSortMode)
            }
          >
            <option value="default">Default (API order)</option>
            <option value="strength">Relationship strength</option>
            <option value="overlap">Overlap signal</option>
            <option value="sameGroup">Same technology group first</option>
          </select>
        </label>
      </div>

      {comparedRelated && (
        <div id="related-patent-comparison" className="comparison-anchor">
          <PatentComparisonPanel
            currentProfile={profile}
            related={comparedRelated}
            onClose={onCloseComparison}
          />
        </div>
      )}

      <ul className="related-card-list">
        {sortedRelated.map((rel) => (
          <RelatedPatentDossierCard
            key={rel.analysis_id}
            rel={rel}
            profileAreas={profile.candidate_application_areas}
            profileAuthority={profile.source_authority || profile.source}
            onCompare={onCompare}
            isCompared={rel.analysis_id === comparedAnalysisId}
          />
        ))}
      </ul>
    </SectionCard>
  );
}

// ---- Technical evidence ----------------------------------------------------

function TechnicalEvidencePanel({ profile }: { profile: PatentProfile }) {
  const [open, setOpen] = useState(false);
  const rows = [...profile.metadata_rows, ...profile.advanced_metadata_rows];
  if (
    profile.keywords.length === 0 &&
    profile.top_terms.length === 0 &&
    !profile.abstract &&
    !profile.claims_preview &&
    rows.length === 0 &&
    profile.ipc_codes.length === 0 &&
    profile.cpc_codes.length === 0
  ) {
    return null;
  }
  return (
    <div className="card technical-evidence">
      <button
        type="button"
        className="card__disclosure technical-evidence__toggle"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
      >
        {open ? "▾" : "▸"} Technical evidence
      </button>
      <p className="technical-evidence__intro">
        Keywords, abstracts, claims preview, and source metadata for deeper
        review.
      </p>
      {open && (
        <div className="card__disclosure-body technical-evidence__body">
          {profile.keywords.length > 0 && (
            <div className="technical-evidence__section">
              <span className="profile-intelligence__label">
                Technical keywords
              </span>
              <KeywordChips
                keywords={profile.keywords}
                max={profile.keywords.length}
              />
            </div>
          )}

          {profile.top_terms.length > 0 && (
            <div className="technical-evidence__section">
              <span className="profile-intelligence__label">
                Top scored terms
              </span>
              <ul className="technical-evidence__term-list">
                {profile.top_terms.map((term) => (
                  <li key={term.term} className="technical-evidence__term">
                    <span className="technical-evidence__term-name">
                      {term.term}
                    </span>
                    <Badge variant={evidenceVariant(term.importance)}>
                      {term.importance}
                    </Badge>
                    <span className="technical-evidence__score">
                      {describeNumber(term.score)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {profile.abstract && (
            <div className="technical-evidence__section">
              <span className="profile-intelligence__label">
                Source abstract
              </span>
              <p className="technical-evidence__text">{profile.abstract}</p>
            </div>
          )}

          {profile.claims_preview && (
            <div className="technical-evidence__section">
              <span className="profile-intelligence__label">
                Claims preview
              </span>
              <p className="technical-evidence__text">
                {profile.claims_preview}
              </p>
            </div>
          )}

          {(profile.ipc_codes.length > 0 || profile.cpc_codes.length > 0) && (
            <div className="technical-evidence__section">
              <span className="profile-intelligence__label">
                Classification codes
              </span>
              <div className="chip-row">
                {profile.ipc_codes.map((code) => (
                  <span key={`ipc-${code}`} className="chip chip--keyword">
                    IPC {code}
                  </span>
                ))}
                {profile.cpc_codes.map((code) => (
                  <span key={`cpc-${code}`} className="chip chip--keyword">
                    CPC {code}
                  </span>
                ))}
              </div>
            </div>
          )}

          {rows.length > 0 && (
            <div className="technical-evidence__section">
              <span className="profile-intelligence__label">
                Source metadata
              </span>
              <table className="metadata-table">
                <tbody>
                  {rows.map((row) => (
                    <tr key={`${row.Field}-${row.Value}`}>
                      <th scope="row">{row.Field}</th>
                      <td>{row.Value || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
