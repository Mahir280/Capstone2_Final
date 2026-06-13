export interface HealthResponse {
  status: string;
  app_name: string;
  api_version: string;
}

export interface MessageResponse {
  status: string;
  message: string;
  details?: Record<string, unknown> | null;
  warnings: string[];
}
