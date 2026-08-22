"use client";

import { useState } from "react";
import {
  CATEGORIES,
  GEO_CATALOG,
  LANGUAGES,
  type ExtractionMode,
  type IntakeForm,
  type StructuredRequest,
} from "@/lib/intakeSchema";
import { emptyIntakeForm, INTAKE_PRESETS } from "@/lib/mockExtract";
import { requestIntakeExtraction } from "@/lib/intakeClient";

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

function modeLabel(mode: ExtractionMode | undefined): string {
  return mode === "gemini" ? "Gemini" : "Mock fallback";
}

export default function IntakePanel() {
  const [form, setForm] = useState<IntakeForm>(emptyIntakeForm);
  const [result, setResult] = useState<StructuredRequest | null>(null);
  const [extractionMode, setExtractionMode] = useState<ExtractionMode | null>(null);
  const [fallbackReason, setFallbackReason] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function extract(nextForm: IntakeForm) {
    setLoading(true);
    setError(null);
    try {
      const response = await requestIntakeExtraction(nextForm);
      setResult(response.record);
      setExtractionMode(response.extraction_mode);
      setFallbackReason(response.fallback_reason);
    } catch (err) {
      setResult(null);
      setExtractionMode(null);
      setFallbackReason(null);
      setError(err instanceof Error ? err.message : "Intake API request failed.");
    } finally {
      setLoading(false);
    }
  }

  function applyPreset(presetId: string) {
    const preset = INTAKE_PRESETS.find((item) => item.id === presetId);
    if (!preset) return;
    const nextForm = { ...preset.form };
    setForm(nextForm);
    void extract(nextForm);
  }

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!form.original_text.trim()) {
      setError("Enter a complaint before submitting.");
      setResult(null);
      setExtractionMode(null);
      return;
    }
    void extract(form);
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
        Complaints are sent to a server route that calls Gemini. The API key
        stays on the server. If Gemini is unavailable, the existing mock
        extractor is used. Nothing is saved.
      </div>

      <div className="preset-row">
        {INTAKE_PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            className="preset-btn"
            disabled={loading}
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
            disabled={loading}
          />
        </label>
        <div className="intake-grid">
          <label>
            Language
            <select
              value={form.language}
              disabled={loading}
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
              disabled={loading}
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
              disabled={loading}
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
        {loading ? <p className="muted">Interpreting complaint…</p> : null}
        <button className="submit-btn" type="submit" disabled={loading}>
          {loading ? "Working…" : "Submit complaint"}
        </button>
      </form>

      {result && extractionMode ? (
        <div className="section card interpretation">
          <h3>Structured interpretation</h3>
          {extractionMode === "gemini" ? (
            <div className="callout ok">Extraction mode: Gemini</div>
          ) : (
            <div className="callout mock-note">
              Extraction mode: Mock fallback
              {fallbackReason ? ` — ${fallbackReason}` : ""}
            </div>
          )}
          {result.review_needed ? (
            <div className="callout tradeoff">
              Review needed — confidence {result.confidence.toFixed(2)} is
              below 0.70. This record should be checked before it feeds demand
              scoring.
            </div>
          ) : (
            <p className="muted">
              Confidence {result.confidence.toFixed(2)} — above the 0.70 review
              threshold. Source: {modeLabel(extractionMode)}.
            </p>
          )}
          <dl className="snapshot-list interpretation-list">
            <Field label="Extraction mode">{modeLabel(extractionMode)}</Field>
            <Field label="Original text">{result.original_text}</Field>
            <Field label="Normalized English">{result.normalized_english}</Field>
            <Field label="Language">{result.language}</Field>
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
          </p>
        </div>
      ) : null}
    </section>
  );
}
