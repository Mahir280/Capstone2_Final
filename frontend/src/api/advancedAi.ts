import { apiPost } from "./client";
import type {
  AdvancedAIRequest,
  AdvancedAIResult,
} from "../types/advancedAi";

export function runAdvancedAIOptimization(
  request: AdvancedAIRequest = {},
  signal?: AbortSignal,
): Promise<AdvancedAIResult> {
  return apiPost<AdvancedAIResult>("/api/advanced-ai/run", request, signal);
}
