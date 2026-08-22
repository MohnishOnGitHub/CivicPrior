import type { CompactProject, DemandCluster, DashboardPayload } from "./types";

export const GEO_COORDINATES_URL = "/data/seed-geo-coordinates.json";

export const MAP_CATEGORIES = ["water", "healthcare", "roads"] as const;
export type MapCategory = (typeof MAP_CATEGORIES)[number];

/** Display-only map styling. Not used by scoring or the optimizer. */
export const HIGH_DEMAND_UNIQUE_MIN = 3;
export const SEVERE_DEFICIT_MIN = 85;

export type GeoCoordinate = {
  geo_id: string;
  location_name: string;
  latitude: number;
  longitude: number;
  synthetic: true;
};

export type GeoCoordinateCatalog = {
  synthetic: boolean;
  coordinate_system: string;
  disclaimer: string;
  locations: GeoCoordinate[];
};

export type MapPoint = {
  id: string;
  geo_id: string;
  location: string;
  category: MapCategory;
  latitude: number;
  longitude: number;
  unique_requests: number;
  request_density: number;
  infrastructure_deficit: number;
  equity_score: number;
  expected_impact: number | null;
  active_investment: number;
  investment_gap: number;
  need_score: number | null;
  cost_cr: number | null;
  project_name: string | null;
  project_id: string | null;
  citizen_demand_summary: string;
  high_demand: boolean;
  severe_deficit: boolean;
  underserved: boolean;
  selected: boolean;
  unmatched: boolean;
};

export async function loadGeoCoordinates(): Promise<GeoCoordinateCatalog> {
  const response = await fetch(GEO_COORDINATES_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Could not load ${GEO_COORDINATES_URL} (${response.status}).`);
  }
  return (await response.json()) as GeoCoordinateCatalog;
}

function isMapCategory(value: string): value is MapCategory {
  return (MAP_CATEGORIES as readonly string[]).includes(value);
}

export function buildMapPoints(
  data: DashboardPayload,
  coordinates: GeoCoordinate[],
  selectedIds: string[],
): MapPoint[] {
  const selected = new Set(selectedIds);
  const byGeoId = new Map(coordinates.map((geo) => [geo.geo_id, geo]));
  const byLocation = new Map(coordinates.map((geo) => [geo.location_name, geo]));
  const projectById = new Map(data.projects.map((project) => [project.id, project]));
  const countsByGeo = new Map<string, number>();

  const points: MapPoint[] = [];

  for (const cluster of data.clusters) {
    const geo = byGeoId.get(cluster.geo_id) ?? byLocation.get(cluster.geography);
    if (!geo || !isMapCategory(cluster.category)) continue;
    const project = cluster.linked_project_id
      ? projectById.get(cluster.linked_project_id) ?? null
      : null;
    const offsetIndex = countsByGeo.get(geo.geo_id) ?? 0;
    countsByGeo.set(geo.geo_id, offsetIndex + 1);
    points.push(
      toMapPoint({
        cluster,
        geo,
        project,
        selected: project ? selected.has(project.id) : false,
        offsetIndex,
      }),
    );
  }

  return points;
}

function toMapPoint({
  cluster,
  geo,
  project,
  selected,
  offsetIndex,
}: {
  cluster: DemandCluster;
  geo: GeoCoordinate;
  project: CompactProject | null | undefined;
  selected: boolean;
  offsetIndex: number;
}): MapPoint {
  const category = cluster.category as MapCategory;
  const offsetLon = offsetIndex * 0.035;
  const unique = cluster.unique_request_count;
  const deficit = cluster.infrastructure_deficit_score;
  const density = cluster.requests_per_1000_residents;
  const summary = [
    `${unique} unique request${unique === 1 ? "" : "s"}`,
    `${density.toFixed(3)} per 1,000 residents`,
    `${cluster.max_urgency} urgency`,
    cluster.requested_intervention.replace(/_/g, " "),
  ].join(" · ");

  return {
    id: cluster.cluster_id,
    geo_id: geo.geo_id,
    location: cluster.geography,
    category,
    latitude: geo.latitude,
    longitude: geo.longitude + offsetLon,
    unique_requests: unique,
    request_density: density,
    infrastructure_deficit: deficit,
    equity_score: project?.equity ?? cluster.equity_index,
    expected_impact: project?.expected_impact ?? null,
    active_investment: cluster.approved_or_active_investment_cr,
    investment_gap: cluster.investment_gap_score,
    need_score: project?.need_score ?? null,
    cost_cr: project?.cost_cr ?? null,
    project_name: project?.name ?? null,
    project_id: project?.id ?? null,
    citizen_demand_summary: summary,
    high_demand: unique >= HIGH_DEMAND_UNIQUE_MIN,
    severe_deficit: deficit >= SEVERE_DEFICIT_MIN,
    underserved: project?.underserved ?? false,
    selected,
    unmatched: !project,
  };
}

export function categoryColor(category: MapCategory): string {
  if (category === "water") return "#2b6cb0";
  if (category === "healthcare") return "#2f855a";
  return "#c05621";
}

export function schematicPosition(
  point: Pick<MapPoint, "latitude" | "longitude">,
  width: number,
  height: number,
): { x: number; y: number } {
  const padX = 56;
  const padY = 48;
  return {
    x: padX + point.longitude * (width - padX * 2),
    y: height - padY - point.latitude * (height - padY * 2),
  };
}
