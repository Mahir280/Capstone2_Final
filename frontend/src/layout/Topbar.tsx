import { useState, type FormEvent } from "react";
import { createSearchParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { fetchHealth } from "../api/health";
import { API_BASE_URL } from "../api/client";

export function Topbar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  // Persistent top-bar search always reaches the Search workflow and seeds it
  // through the `q` query parameter. Shared patent filters are intentionally
  // omitted because Search maintains its own query state.
  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    navigate({
      pathname: "/search",
      search: trimmed ? `?${createSearchParams({ q: trimmed })}` : "",
    });
  };

  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 0,
  });

  let statusLabel = "Checking backend...";
  let statusVariant: "ok" | "warn" | "error" = "warn";
  let statusTitle = statusLabel;

  if (healthQuery.isError) {
    const target = API_BASE_URL || "same origin";
    statusLabel = "Backend unreachable";
    statusTitle = `Backend unreachable at ${target}`;
    statusVariant = "error";
  } else if (healthQuery.data) {
    statusLabel = `Backend online · ${healthQuery.data.api_version}`;
    statusTitle = `${healthQuery.data.app_name} (API ${healthQuery.data.api_version})`;
    statusVariant = "ok";
  }

  return (
    <header className="app-topbar">
      <div className="app-topbar__left">
        <div className="app-topbar__heading">
          <div className="app-topbar__eyebrow">
            Patent intelligence workspace
          </div>
          <div className="app-topbar__title">
            Fiber-Based Wearable Electronics
          </div>
        </div>
      </div>
      <form
        className="app-topbar__search"
        role="search"
        aria-label="Search patents"
        onSubmit={handleSearchSubmit}
      >
        <svg
          className="app-topbar__search-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          className="app-topbar__search-input"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search patents…"
          autoComplete="off"
          aria-label="Search patents"
        />
      </form>
      <div className="app-topbar__right">
        <span
          className={`status-pill status-pill--${statusVariant}`}
          title={statusTitle}
          aria-label={statusTitle}
        >
          <span className="status-pill__dot" aria-hidden="true" />
          <span>{statusLabel}</span>
        </span>
      </div>
    </header>
  );
}
