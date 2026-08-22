import {
  CATEGORIES,
  GEO_CATALOG,
  INTERVENTIONS_BY_CATEGORY,
  LANGUAGES,
  SUBCATEGORIES_BY_CATEGORY,
  URGENCY_CLASSES,
  type IntakeForm,
  type StructuredRequest,
} from "./intakeSchema";
import { structuredRecordFromModel } from "./validateIntake";

export const GEMINI_MODEL = "gemini-3.6-flash";

const GEMINI_ENDPOINT = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`;

function catalogBlock(): string {
  const geos = GEO_CATALOG.map((geo) => `${geo.id} (${geo.name})`).join(", ");
  const languages = LANGUAGES.map((language) => language.id).join(", ");
  const subcats = CATEGORIES.map(
    (category) => `${category}: ${SUBCATEGORIES_BY_CATEGORY[category].join(", ")}`,
  ).join(" | ");
  const interventions = CATEGORIES.map(
    (category) => `${category}: ${INTERVENTIONS_BY_CATEGORY[category].join(", ")}`,
  ).join(" | ");
  return [
    `languages: ${languages}`,
    `categories: ${CATEGORIES.join(", ")}`,
    `subcategories: ${subcats}`,
    `interventions: ${interventions}`,
    `urgency_class: ${URGENCY_CLASSES.join(", ")}`,
    `geo_id values: ${geos}`,
  ].join("\n");
}

function buildPrompt(form: IntakeForm): string {
  return [
    "You convert a citizen infrastructure complaint into one CivicPrior intake record.",
    "This is decision-support intake only. Do not invent projects, budgets, or unsupported infrastructure types.",
    "",
    "Rules:",
    "- Preserve the citizen's meaning. Do not rewrite the complaint into a different issue.",
    "- normalized_english must be a faithful English translation or normalization of the complaint.",
    "- Use only the allowed enum values below. If nothing fits, pick the closest allowed value.",
    "- If the place is not in the geography catalog, pick the closest geo_id and set geography_uncertain=true.",
    "- If category is unclear, pick the closest supported category (water, healthcare, roads) and set category_uncertain=true.",
    "- If the complaint could be two supported categories (for example a hospital road, ambulance access, or clinic plus road), pick the closest one, set category_uncertain=true, and keep confidence below 0.70.",
    "- If the request is outside water, healthcare, and roads (metro, airport, electricity, housing, billing), pick the closest allowed category, set category_uncertain=true, and keep confidence well below 0.70.",
    "- If you are uncertain, return low confidence (below 0.70).",
    "- Do not invent metros, airports, housing, electricity, or other unsupported infrastructure types.",
    "- requested_intervention must belong to the chosen category.",
    "",
    "Allowed values:",
    catalogBlock(),
    "",
    "Citizen complaint:",
    form.original_text.trim(),
    "",
    `UI language hint: ${form.language}`,
    `UI locality hint: ${form.geo_id || "(none)"}`,
    `UI category hint: ${form.category_hint || "(none)"}`,
    "",
    "Return JSON only.",
  ].join("\n");
}

const RESPONSE_SCHEMA = {
  type: "OBJECT",
  properties: {
    normalized_english: { type: "STRING" },
    language: { type: "STRING", enum: LANGUAGES.map((language) => language.id) },
    category: { type: "STRING", enum: [...CATEGORIES] },
    subcategory: { type: "STRING" },
    location_text: { type: "STRING" },
    geo_id: { type: "STRING", enum: GEO_CATALOG.map((geo) => geo.id) },
    urgency_class: { type: "STRING", enum: [...URGENCY_CLASSES] },
    requested_intervention: { type: "STRING" },
    confidence: { type: "NUMBER" },
    geography_uncertain: { type: "BOOLEAN" },
    category_uncertain: { type: "BOOLEAN" },
  },
  required: [
    "normalized_english",
    "language",
    "category",
    "subcategory",
    "location_text",
    "geo_id",
    "urgency_class",
    "requested_intervention",
    "confidence",
  ],
};

function parseModelText(text: string): unknown {
  const trimmed = text.trim();
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = fenced ? fenced[1].trim() : trimmed;
  return JSON.parse(candidate) as unknown;
}

export async function extractWithGemini(
  form: IntakeForm,
  apiKey: string,
): Promise<StructuredRequest> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  let response: Response;
  try {
    response = await fetch(GEMINI_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": apiKey,
      },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: buildPrompt(form) }] }],
        generationConfig: {
          temperature: 0.1,
          responseMimeType: "application/json",
          responseSchema: RESPONSE_SCHEMA,
        },
      }),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Gemini HTTP ${response.status}: ${detail.slice(0, 300)}`);
  }

  const body = (await response.json()) as {
    candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
  };
  const text = body.candidates?.[0]?.content?.parts
    ?.map((part) => part.text ?? "")
    .join("")
    .trim();
  if (!text) {
    throw new Error("Gemini returned an empty response");
  }

  let parsed: unknown;
  try {
    parsed = parseModelText(text);
  } catch {
    throw new Error("Gemini response was not valid JSON");
  }

  return structuredRecordFromModel(parsed, form, "gemini", null);
}
