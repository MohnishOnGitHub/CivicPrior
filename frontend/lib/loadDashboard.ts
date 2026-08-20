import type { DashboardPayload } from "./types";

export const DASHBOARD_DATA_URL = "/data/dashboard-v01.json";

export async function loadDashboard(): Promise<DashboardPayload> {
  const response = await fetch(DASHBOARD_DATA_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(
      `Could not load ${DASHBOARD_DATA_URL} (${response.status}). Run python3 src/pipeline/export_dashboard.py from the repo root.`,
    );
  }
  return (await response.json()) as DashboardPayload;
}
