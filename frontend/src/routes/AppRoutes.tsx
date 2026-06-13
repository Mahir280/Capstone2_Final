import { Suspense, lazy } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppLayout } from "../layout/AppLayout";
import { LoadingState } from "../components/common/LoadingState";
import { AdvancedAIPage } from "../pages/AdvancedAIPage";
import { DataSourcesPage } from "../pages/DataSourcesPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { OverviewPage } from "../pages/OverviewPage";
import { PatentLandscapePage } from "../pages/PatentLandscapePage";
import { PatentProfilePage } from "../pages/PatentProfilePage";
import { PatentSearchPage } from "../pages/PatentSearchPage";

// Lazy-loaded so the ECharts bundle is only fetched when the analytics route is
// visited, keeping it out of the initial app chunk.
const VisualAnalyticsPage = lazy(() =>
  import("../pages/VisualAnalyticsPage").then((module) => ({
    default: module.VisualAnalyticsPage,
  })),
);

// Redirect the legacy /overview path to home while preserving shared filters.
function RedirectToHome() {
  const location = useLocation();
  return <Navigate to={{ pathname: "/", search: location.search }} replace />;
}

// Redirect the legacy /insights route to Trends & Players while preserving
// shared filters.
function RedirectToAnalytics() {
  const location = useLocation();
  return (
    <Navigate to={{ pathname: "/analytics", search: location.search }} replace />
  );
}

// Redirect the legacy frontend route /landscape to /map. The API path remains
// /api/landscape, and the query string preserves filters and `focus` deep-links.
function RedirectToMap() {
  const location = useLocation();
  return <Navigate to={{ pathname: "/map", search: location.search }} replace />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="/search" element={<PatentSearchPage />} />
        <Route path="/overview" element={<RedirectToHome />} />
        <Route path="/patents/:analysisId" element={<PatentProfilePage />} />
        <Route path="/map" element={<PatentLandscapePage />} />
        <Route path="/landscape" element={<RedirectToMap />} />
        <Route path="/insights" element={<RedirectToAnalytics />} />
        <Route
          path="/analytics"
          element={
            <Suspense fallback={<LoadingState message="Loading analytics..." />}>
              <VisualAnalyticsPage />
            </Suspense>
          }
        />
        <Route path="/advanced-ai" element={<AdvancedAIPage />} />
        <Route path="/data-sources" element={<DataSourcesPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
