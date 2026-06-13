import { apiGet } from "./client";
import type { HealthResponse } from "../types/common";

export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health", undefined, signal);
}
