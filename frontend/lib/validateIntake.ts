import {
  AMBIGUOUS_CONFIDENCE_MAX,
  GEO_CATALOG,
  allowedInterventions,
  allowedSubcategories,
  catalogGeoIds,
  geoName,
  isCategoryId,
  isLanguageId,
  isUrgencyClass,
  type CategoryId,
  type ExtractionMode,
  type IntakeForm,
  type StructuredRequest,
} from "./intakeSchema";

function asString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function resolveGeoId(rawGeoId: string, locationText: string, hintGeoId: string): {
  geoId: string;
  uncertain: boolean;
} {
  const ids = catalogGeoIds();
  if (ids.includes(rawGeoId)) {
    return { geoId: rawGeoId, uncertain: false };
  }

  const haystack = `${rawGeoId} ${locationText}`.toLowerCase();
  const byName = GEO_CATALOG.find((geo) => haystack.includes(geo.name.toLowerCase()));
  if (byName) {
    return { geoId: byName.id, uncertain: rawGeoId !== byName.id };
  }

  if (ids.includes(hintGeoId)) {
    return { geoId: hintGeoId, uncertain: true };
  }

  return { geoId: "geo_ward_17", uncertain: true };
}

export function structuredRecordFromModel(
  raw: unknown,
  form: IntakeForm,
  extractionMode: ExtractionMode = "gemini",
  fallbackReason: string | null = null,
): StructuredRequest {
  if (!raw || typeof raw !== "object") {
    throw new Error("Model output is not an object");
  }

  const payload = raw as Record<string, unknown>;
  const originalText = form.original_text.trim();
  if (!originalText) {
    throw new Error("original_text is required");
  }

  const normalizedEnglish = asString(payload.normalized_english);
  if (!normalizedEnglish) {
    throw new Error("normalized_english is required");
  }

  const rawLanguage = asString(payload.language);
  const language = isLanguageId(rawLanguage) ? rawLanguage : form.language;

  const hintedCategory = form.category_hint && isCategoryId(form.category_hint)
    ? form.category_hint
    : null;
  const rawCategory = asString(payload.category);
  let category: CategoryId;
  let categoryUncertain = payload.category_uncertain === true;
  if (isCategoryId(rawCategory)) {
    category = rawCategory;
  } else if (hintedCategory) {
    category = hintedCategory;
    categoryUncertain = true;
  } else {
    throw new Error(`Unsupported category: ${rawCategory || "(empty)"}`);
  }

  const subcategories = allowedSubcategories(category);
  const interventions = allowedInterventions(category);
  let subcategory = asString(payload.subcategory);
  let intervention = asString(payload.requested_intervention);
  if (!subcategories.includes(subcategory)) {
    subcategory = subcategories[0];
    categoryUncertain = true;
  }
  if (!interventions.includes(intervention)) {
    intervention = interventions[0];
    categoryUncertain = true;
  }

  const locationText =
    asString(payload.location_text) || geoName(form.geo_id) || "Unknown locality";
  const geoResolved = resolveGeoId(asString(payload.geo_id), locationText, form.geo_id);
  const geographyUncertain =
    payload.geography_uncertain === true || geoResolved.uncertain;

  const rawUrgency = asString(payload.urgency_class);
  const urgency = isUrgencyClass(rawUrgency) ? rawUrgency : "medium";

  let confidence = asNumber(payload.confidence);
  if (confidence === null) {
    throw new Error("confidence is required");
  }
  confidence = Math.min(1, Math.max(0, confidence));
  if (categoryUncertain || geographyUncertain) {
    confidence = Math.min(confidence, 0.62);
  }

  const reviewNeeded = confidence < AMBIGUOUS_CONFIDENCE_MAX;

  return {
    id: `INTAKE-${Date.now().toString(36).toUpperCase()}`,
    original_text: originalText,
    language,
    normalized_english: normalizedEnglish,
    category,
    subcategory,
    location_text: locationText,
    geo_id: geoResolved.geoId,
    canonical_location: geoName(geoResolved.geoId),
    urgency_class: urgency,
    requested_intervention: intervention,
    confidence: Number(confidence.toFixed(2)),
    submitted_at: new Date().toISOString(),
    synthetic: true,
    review_needed: reviewNeeded,
    matched_preset: null,
    extraction_mode: extractionMode,
    fallback_reason: fallbackReason,
  };
}
