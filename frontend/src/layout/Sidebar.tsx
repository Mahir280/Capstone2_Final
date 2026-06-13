import { NavLink } from "react-router-dom";

import { useFilters } from "../state/FilterProvider";

interface NavItem {
  to: string;
  label: string;
  end?: boolean;
  tone?: "support";
  // Filter-aware destinations carry active patent filters in their links.
  // Search keeps its own `q` workflow, while Data & Methods uses plain paths.
  filterAware?: boolean;
}

// Primary destinations reflect the app's four main user intents. Overview is
// the home route; Overview, Map, and Trends carry shared filters, while Search
// uses its separate `q`-keyed workflow.
const PRIMARY_ITEMS: NavItem[] = [
  { to: "/", label: "Overview", end: true, filterAware: true },
  { to: "/map", label: "Map", filterAware: true },
  { to: "/analytics", label: "Trends & Players", filterAware: true },
  { to: "/search", label: "Search" },
];

// Secondary Data & Methods area for housekeeping and academic-evidence
// surfaces, visually de-emphasized so they do not compete with the primary flow.
const DATA_METHODS_ITEMS: NavItem[] = [
  { to: "/data-sources", label: "Corpus & Sources", tone: "support" },
  { to: "/advanced-ai", label: "Method & Validation", tone: "support" },
];

function NavSection({
  label,
  items,
  filterSearch,
}: {
  label?: string;
  items: NavItem[];
  filterSearch: string;
}) {
  return (
    <>
      {label && <div className="app-sidebar__section-label">{label}</div>}
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={
            item.filterAware && filterSearch
              ? { pathname: item.to, search: filterSearch }
              : item.to
          }
          end={item.end}
          className={({ isActive }) => {
            const classes = ["app-sidebar__link"];
            if (item.tone) classes.push(`app-sidebar__link--${item.tone}`);
            if (isActive) classes.push("app-sidebar__link--active");
            return classes.join(" ");
          }}
        >
          <span className="app-sidebar__link-text">
            <span>{item.label}</span>
          </span>
        </NavLink>
      ))}
    </>
  );
}

export function Sidebar() {
  const { filterSearch } = useFilters();
  return (
    <aside className="app-sidebar" aria-label="Primary navigation">
      <div className="app-sidebar__brand">
        <div className="app-sidebar__brand-mark" aria-hidden="true">
          FW
        </div>
        <div className="app-sidebar__brand-text">
          <span className="app-sidebar__brand-title">
            Fiber Wearable Patents
          </span>
          <span className="app-sidebar__brand-sub">
            Patent intelligence workspace
          </span>
        </div>
      </div>
      <nav className="app-sidebar__nav">
        <NavSection items={PRIMARY_ITEMS} filterSearch={filterSearch} />
        <NavSection
          label="Data & Methods"
          items={DATA_METHODS_ITEMS}
          filterSearch={filterSearch}
        />
      </nav>
      <div className="app-sidebar__footer">
        <strong>Decision-support only.</strong>
        <br />
        Not legal advice.
      </div>
    </aside>
  );
}
