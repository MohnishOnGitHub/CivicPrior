import { NextResponse } from "next/server";
import { runIntakeExtraction } from "@/lib/intakeExtract";
import type { IntakeForm } from "@/lib/intakeSchema";

export const runtime = "nodejs";

export async function POST(request: Request) {
  let body: Partial<IntakeForm>;
  try {
    body = (await request.json()) as Partial<IntakeForm>;
  } catch {
    return NextResponse.json(
      { error: "Request body must be JSON." },
      { status: 400 },
    );
  }

  const form: IntakeForm = {
    original_text: typeof body.original_text === "string" ? body.original_text : "",
    language: body.language === "hi" || body.language === "te" ? body.language : "en",
    geo_id: typeof body.geo_id === "string" ? body.geo_id : "geo_ward_17",
    category_hint:
      body.category_hint === "water" ||
      body.category_hint === "healthcare" ||
      body.category_hint === "roads"
        ? body.category_hint
        : "",
  };

  if (!form.original_text.trim()) {
    return NextResponse.json(
      { error: "Enter a complaint before submitting." },
      { status: 400 },
    );
  }

  try {
    const result = await runIntakeExtraction(form);
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Intake extraction failed.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
