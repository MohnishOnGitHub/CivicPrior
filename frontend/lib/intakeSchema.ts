export const LANGUAGES = [
  { id: "en", label: "English" },
  { id: "hi", label: "Hindi" },
  { id: "te", label: "Telugu" },
] as const;

export const CATEGORIES = ["water", "healthcare", "roads"] as const;

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
  urgency_class: "low" | "medium" | "high" | "critical";
  requested_intervention: string;
  confidence: number;
  submitted_at: string;
  synthetic: true;
  review_needed: boolean;
  matched_preset: string | null;
};

export type IntakePreset = {
  id: string;
  label: string;
  form: IntakeForm;
  record: Omit<
    StructuredRequest,
    "id" | "submitted_at" | "review_needed" | "matched_preset" | "original_text"
  > & { original_text: string };
};
