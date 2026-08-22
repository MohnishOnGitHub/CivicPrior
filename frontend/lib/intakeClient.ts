import type { IntakeExtractResponse, IntakeForm } from "./intakeSchema";

export async function requestIntakeExtraction(
  form: IntakeForm,
): Promise<IntakeExtractResponse> {
  const response = await fetch("/api/intake/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });

  const payload = (await response.json()) as IntakeExtractResponse & {
    error?: string;
  };

  if (!response.ok) {
    throw new Error(payload.error || `Intake API failed (${response.status})`);
  }

  if (!payload.record || !payload.extraction_mode) {
    throw new Error("Intake API returned an incomplete result.");
  }

  return payload;
}
