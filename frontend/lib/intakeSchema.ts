export const LANGUAGES = [
  { id: "en", label: "English" },
  { id: "hi", label: "Hindi" },
  { id: "te", label: "Telugu" },
] as const;

export const CATEGORIES = ["water", "healthcare", "roads"] as const;

export const URGENCY_CLASSES = ["low", "medium", "high", "critical"] as const;

export const SUBCATEGORIES_BY_CATEGORY = {
  water: ["supply_reliability", "water_quality", "piped_access", "storage_capacity"],
  healthcare: ["facility_capacity", "staffing", "local_access", "service_quality"],
  roads: [
    "all_weather_connectivity",
    "congestion",
    "pavement_condition",
    "junction_bottleneck",
  ],
} as const;

export const INTERVENTIONS_BY_CATEGORY = {
  water: [
    "water_distribution_upgrade",
    "municipal_water_storage_expansion",
    "rural_drinking_water_pipeline",
    "water_treatment_plant_upgrade",
  ],
  healthcare: [
    "rural_phc_expansion",
    "phc_renovation",
    "community_health_subcentre",
    "district_phc_staffing_upgrade",
  ],
  roads: [
    "urban_road_expansion",
    "village_road_connectivity",
    "urban_flyover_improvement",
    "main_road_resurfacing",
  ],
} as const;

export const GEO_CATALOG: Array<{ id: string; name: string }> = [
  { id: "geo_ward_17", name: "Ward 17" },
  { id: "geo_ward_9", name: "Ward 9" },
  { id: "geo_central_zone", name: "Central Zone" },
  { id: "geo_north_zone", name: "North Zone" },
  { id: "geo_south_zone", name: "South Zone" },
  { id: "geo_east_zone", name: "East Zone" },
  { id: "geo_commercial_district", name: "Commercial District" },
  { id: "geo_rural_block_a", name: "Rural Block A" },
  { id: "geo_rural_block_c", name: "Rural Block C" },
  { id: "geo_village_cluster_b", name: "Village Cluster B" },
  { id: "geo_village_cluster_d", name: "Village Cluster D" },
  { id: "geo_district_periphery", name: "District Periphery" },
];

export const AMBIGUOUS_CONFIDENCE_MAX = 0.7;

export type LanguageId = (typeof LANGUAGES)[number]["id"];
export type CategoryId = (typeof CATEGORIES)[number];
export type UrgencyClass = (typeof URGENCY_CLASSES)[number];
export type ExtractionMode = "gemini" | "mock_fallback";

export type IntakeForm = {
  original_text: string;
  language: LanguageId;
  geo_id: string;
  category_hint: CategoryId | "";
};

export type StructuredRequest = {
  id: string;
  original_text: string;
  language: LanguageId;
  normalized_english: string;
  category: CategoryId;
  subcategory: string;
  location_text: string;
  geo_id: string;
  canonical_location: string;
  urgency_class: UrgencyClass;
  requested_intervention: string;
  confidence: number;
  submitted_at: string;
  synthetic: true;
  review_needed: boolean;
  matched_preset: string | null;
  extraction_mode?: ExtractionMode;
  fallback_reason?: string | null;
};

export type IntakeExtractResponse = {
  extraction_mode: ExtractionMode;
  fallback_reason: string | null;
  record: StructuredRequest;
};

export type IntakePreset = {
  id: string;
  label: string;
  form: IntakeForm;
  record: Omit<
    StructuredRequest,
    | "id"
    | "submitted_at"
    | "review_needed"
    | "matched_preset"
    | "original_text"
    | "extraction_mode"
    | "fallback_reason"
  > & { original_text: string };
};

export function geoName(geoId: string): string {
  return GEO_CATALOG.find((geo) => geo.id === geoId)?.name ?? geoId;
}

export function isLanguageId(value: string): value is LanguageId {
  return LANGUAGES.some((language) => language.id === value);
}

export function isCategoryId(value: string): value is CategoryId {
  return (CATEGORIES as readonly string[]).includes(value);
}

export function isUrgencyClass(value: string): value is UrgencyClass {
  return (URGENCY_CLASSES as readonly string[]).includes(value);
}

export function allowedSubcategories(category: CategoryId): readonly string[] {
  return SUBCATEGORIES_BY_CATEGORY[category];
}

export function allowedInterventions(category: CategoryId): readonly string[] {
  return INTERVENTIONS_BY_CATEGORY[category];
}

export function catalogGeoIds(): string[] {
  return GEO_CATALOG.map((geo) => geo.id);
}
