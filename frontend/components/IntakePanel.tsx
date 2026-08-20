"use client";

import { useState } from "react";
import {
  CATEGORIES,
  GEO_CATALOG,
  LANGUAGES,
  type IntakeForm,
  type StructuredRequest,
} from "@/lib/intakeSchema";
import { emptyIntakeForm, extractStructuredRequest, INTAKE_PRESETS } from "@/lib/mockExtract";

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export default function IntakePanel() {
  const [form, setForm] = useState<IntakeForm>(emptyIntakeForm);
  const [result, setResult] = useState<StructuredRequest | null>(null);
  const [error, setError] = useState<string | null>(null);

  function applyPreset(presetId: string) {
    const preset = INTAKE_PRESETS.find((item) => item.id === presetId);
    if (!preset) return;
    setForm({ ...preset.form });
    setError(null);
    setResult(extractStructuredRequest(preset.form));
  }

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!form.original_text.trim()) {
      setError("Enter a complaint before submitting.");
      setResult(null);
      return;
    }
    setError(null);
    setResult(extractStructuredRequest(form));
  }

  return (
    <section>
      <div className="page-head">
        <div>
          <h2>Citizen intake</h2>
          <p>
            CivicPrior uses AI to understand citizen requests. Funding decisions
            are made later using evidence + optimization, not directly by the
            language model.
          </p>
        </div>
      </div>

      <div className="callout mock-note">
        Demo / mock extraction — Gemini integration pending. This screen does
        not write to seed-citizen-requests.json.
      </div>

      <div className="preset-row">
        {INTAKE_PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            className="preset-btn"
            onClick={() => applyPreset(preset.id)}
          >
            {preset.label}
          </button>
        ))}
      </div>

      <form className="intake-form card" onSubmit={onSubmit}>
        <label>
          Complaint
          <textarea
            rows={5}
            value={form.original_text}
            onChange={(event) =>
              setForm((current) => ({ ...current, original_text: event.target.value }))
            }
            placeholder="Describe the local infrastructure problem…"
          />
        </label>
        <div className="intake-grid">
          <label>
            Language
            <select
              value={form.language}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  language: event.target.value as IntakeForm["language"],
                }))
              }
            >
              {LANGUAGES.map((language) => (
                <option key={language.id} value={language.id}>
                  {language.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Locality
            <select
              value={form.geo_id}
              onChange={(event) =>
                setForm((current) => ({ ...current, geo_id: event.target.value }))
              }
            >
              {GEO_CATALOG.map((geo) => (
                <option key={geo.id} value={geo.id}>
                  {geo.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Category hint (optional)
            <select
              value={form.category_hint}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  category_hint: event.target.value as IntakeForm["category_hint"],
                }))
              }
            >
              <option value="">None</option>
              {CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
        </div>
        {error ? <p className="form-error">{error}</p> : null}
        <button className="submit-btn" type="submit">
          Submit complaint
        </button>
      </form>

      {result ? (
        <div className="section card interpretation">
          <h3>Structured interpretation</h3>
          {result.review_needed ? (
            <div className="callout tradeoff">
              Review needed — mock confidence {result.confidence.toFixed(2)} is
              below 0.70. A live extractor should send this to a human reviewer.
            </div>
          ) : (
            <p className="muted">
              Confidence {result.confidence.toFixed(2)} — above the 0.70 review
              threshold.
            </p>
          )}
          <dl className="snapshot-list interpretation-list">
            <Field label="Original text">{result.original_text}</Field>
            <Field label="Normalized English">{result.normalized_english}</Field>
            <Field label="Category">{result.category}</Field>
            <Field label="Subcategory">{result.subcategory}</Field>
            <Field label="Location">{result.canonical_location}</Field>
            <Field label="Urgency">{result.urgency_class}</Field>
            <Field label="Requested intervention">{result.requested_intervention}</Field>
            <Field label="Confidence">{result.confidence.toFixed(2)}</Field>
            <Field label="Review needed">{result.review_needed ? "yes" : "no"}</Field>
          </dl>
          <p className="muted">
            Demo record {result.id}. Not saved to the citizen-request seed file.
            {result.matched_preset
              ? ` Matched demo pattern: ${result.matched_preset}.`
              : " No known demo pattern matched."}
          </p>
        </div>
      ) : null}
    </section>
  );
}
