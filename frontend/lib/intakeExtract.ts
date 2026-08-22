import { extractWithGemini } from "./gemini";
import type { IntakeExtractResponse, IntakeForm } from "./intakeSchema";
import { extractStructuredRequest } from "./mockExtract";

function mockFallback(form: IntakeForm, reason: string): IntakeExtractResponse {
  const record = extractStructuredRequest(form);
  record.extraction_mode = "mock_fallback";
  record.fallback_reason = reason;
  return {
    extraction_mode: "mock_fallback",
    fallback_reason: reason,
    record,
  };
}

export async function runIntakeExtraction(
  form: IntakeForm,
): Promise<IntakeExtractResponse> {
  const text = form.original_text?.trim() ?? "";
  if (!text) {
    throw new Error("Enter a complaint before submitting.");
  }

  const safeForm: IntakeForm = {
    ...form,
    original_text: text,
  };

  const apiKey = process.env.GEMINI_API_KEY?.trim();
  if (!apiKey) {
    return mockFallback(safeForm, "GEMINI_API_KEY is missing");
  }

  try {
    const record = await extractWithGemini(safeForm, apiKey);
    return {
      extraction_mode: "gemini",
      fallback_reason: null,
      record,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Gemini extraction failed";
    return mockFallback(safeForm, message);
  }
}
