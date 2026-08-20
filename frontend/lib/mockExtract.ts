/**
 * Deterministic mock extractor for the citizen intake demo.
 * Does not call Gemini and does not write seed-citizen-requests.json.
 */

import {
  AMBIGUOUS_CONFIDENCE_MAX,
  GEO_CATALOG,
  type CategoryId,
  type IntakeForm,
  type IntakePreset,
  type StructuredRequest,
} from "./intakeSchema";

const FALLBACK_BY_CATEGORY: Record<
  CategoryId,
  { subcategory: string; intervention: string }
> = {
  water: {
    subcategory: "supply_reliability",
    intervention: "water_distribution_upgrade",
  },
  healthcare: {
    subcategory: "local_access",
    intervention: "phc_renovation",
  },
  roads: {
    subcategory: "pavement_condition",
    intervention: "main_road_resurfacing",
  },
};

export const INTAKE_PRESETS: IntakePreset[] = [
  {
    id: "ward17-water",
    label: "Ward 17 water supply",
    form: {
      original_text:
        "In Ward 17 the taps run only twice a week. The old pipes leak so much that the last streets get nothing.",
      language: "en",
      geo_id: "geo_ward_17",
      category_hint: "water",
    },
    record: {
      original_text:
        "In Ward 17 the taps run only twice a week. The old pipes leak so much that the last streets get nothing.",
      language: "en",
      normalized_english:
        "Ward 17 piped water is available only twice a week because leaking distribution pipes leave the last streets without supply.",
      category: "water",
      subcategory: "supply_reliability",
      location_text: "Ward 17",
      geo_id: "geo_ward_17",
      canonical_location: "Ward 17",
      urgency_class: "high",
      requested_intervention: "water_distribution_upgrade",
      confidence: 0.94,
      synthetic: true,
    },
  },
  {
    id: "block-a-phc",
    label: "Rural Block A PHC access",
    form: {
      original_text:
        "Rural Block A PHC is overflowing. People wait outside from 7am and there are not enough beds.",
      language: "en",
      geo_id: "geo_rural_block_a",
      category_hint: "healthcare",
    },
    record: {
      original_text:
        "Rural Block A PHC is overflowing. People wait outside from 7am and there are not enough beds.",
      language: "en",
      normalized_english:
        "Rural Block A primary health centre is overcrowded, with long morning queues and insufficient beds.",
      category: "healthcare",
      subcategory: "facility_capacity",
      location_text: "Rural Block A",
      geo_id: "geo_rural_block_a",
      canonical_location: "Rural Block A",
      urgency_class: "high",
      requested_intervention: "rural_phc_expansion",
      confidence: 0.92,
      synthetic: true,
    },
  },
  {
    id: "cluster-b-roads",
    label: "Village Cluster B road access",
    form: {
      original_text:
        "Village Cluster B has no all-weather road. In the rains we carry patients on a cot to the main road.",
      language: "en",
      geo_id: "geo_village_cluster_b",
      category_hint: "roads",
    },
    record: {
      original_text:
        "Village Cluster B has no all-weather road. In the rains we carry patients on a cot to the main road.",
      language: "en",
      normalized_english:
        "Village Cluster B lacks an all-weather road; patients are carried to the main road during rains.",
      category: "roads",
      subcategory: "all_weather_connectivity",
      location_text: "Village Cluster B",
      geo_id: "geo_village_cluster_b",
      canonical_location: "Village Cluster B",
      urgency_class: "high",
      requested_intervention: "village_road_connectivity",
      confidence: 0.93,
      synthetic: true,
    },
  },
  {
    id: "ward9-ambiguous",
    label: "Ambiguous hospital-road complaint",
    form: {
      original_text:
        "The road to the Ward 9 hospital is broken and ambulances bounce. Fix the road or the hospital access will suffer.",
      language: "en",
      geo_id: "geo_ward_9",
      category_hint: "",
    },
    record: {
      original_text:
        "The road to the Ward 9 hospital is broken and ambulances bounce. Fix the road or the hospital access will suffer.",
      language: "en",
      normalized_english:
        "The access road to Ward 9 hospital is broken and rough for ambulances; whether this is a roads or healthcare request is unclear.",
      category: "roads",
      subcategory: "pavement_condition",
      location_text: "Ward 9 hospital road",
      geo_id: "geo_ward_9",
      canonical_location: "Ward 9",
      urgency_class: "medium",
      requested_intervention: "main_road_resurfacing",
      confidence: 0.58,
      synthetic: true,
    },
  },
];

function normalize(text: string): string {
  return text.trim().toLowerCase().replace(/\s+/g, " ");
}

function geoName(geoId: string): string {
  return GEO_CATALOG.find((geo) => geo.id === geoId)?.name ?? geoId;
}

function finalize(
  base: Omit<StructuredRequest, "id" | "submitted_at" | "review_needed" | "matched_preset">,
  presetId: string | null,
): StructuredRequest {
  return {
    ...base,
    id: `DEMO-${Date.now().toString(36).toUpperCase()}`,
    submitted_at: new Date().toISOString(),
    review_needed: base.confidence < AMBIGUOUS_CONFIDENCE_MAX,
    matched_preset: presetId,
  };
}

function keywordScore(text: string, presetId: string): number {
  const haystack = normalize(text);
  const needles: Record<string, string[]> = {
    "ward17-water": ["ward 17", "tap", "pipe", "water", "leak"],
    "block-a-phc": ["block a", "phc", "bed", "doctor", "hospital", "health"],
    "cluster-b-roads": ["cluster b", "monsoon", "mud", "all-weather", "road"],
    "ward9-ambiguous": ["ward 9", "ambulance", "hospital", "broken"],
  };
  return (needles[presetId] ?? []).filter((word) => haystack.includes(word)).length;
}

export function extractStructuredRequest(form: IntakeForm): StructuredRequest {
  const text = form.original_text.trim();
  const exact = INTAKE_PRESETS.find(
    (preset) => normalize(preset.form.original_text) === normalize(text),
  );
  if (exact) {
    return finalize(
      {
        ...exact.record,
        original_text: text,
        language: form.language,
        geo_id: form.geo_id || exact.record.geo_id,
        canonical_location: geoName(form.geo_id || exact.record.geo_id),
        location_text: geoName(form.geo_id || exact.record.geo_id),
        synthetic: true,
      },
      exact.id,
    );
  }

  const ranked = INTAKE_PRESETS.map((preset) => {
    const sameGeo = form.geo_id === preset.record.geo_id ? 2 : 0;
    const sameHint =
      form.category_hint && form.category_hint === preset.record.category ? 2 : 0;
    return { preset, score: sameGeo + sameHint + keywordScore(text, preset.id) };
  }).sort((a, b) => b.score - a.score);

  const best = ranked[0];
  if (best && best.score >= 4) {
    return finalize(
      {
        ...best.preset.record,
        original_text: text,
        language: form.language,
        normalized_english: `${best.preset.record.normalized_english} (matched from a known demo pattern; not a live model).`,
        geo_id: form.geo_id || best.preset.record.geo_id,
        canonical_location: geoName(form.geo_id || best.preset.record.geo_id),
        location_text: geoName(form.geo_id || best.preset.record.geo_id),
        confidence: Math.min(best.preset.record.confidence, 0.78),
        synthetic: true,
      },
      best.preset.id,
    );
  }

  const category: CategoryId = form.category_hint || "roads";
  const fallback = FALLBACK_BY_CATEGORY[category];
  const location = geoName(form.geo_id);
  return finalize(
    {
      original_text: text,
      language: form.language,
      normalized_english:
        "Unmatched demo text. The mock extractor could not map this complaint to a known gold example, so fields are a low-confidence placeholder.",
      category,
      subcategory: fallback.subcategory,
      location_text: location,
      geo_id: form.geo_id,
      canonical_location: location,
      urgency_class: "medium",
      requested_intervention: fallback.intervention,
      confidence: 0.42,
      synthetic: true,
    },
    null,
  );
}

export function emptyIntakeForm(): IntakeForm {
  return {
    original_text: "",
    language: "en",
    geo_id: "geo_ward_17",
    category_hint: "",
  };
}
