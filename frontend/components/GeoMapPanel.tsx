"use client";

import { useEffect, useMemo, useState } from "react";
import type { DashboardPayload, ScenarioResult } from "@/lib/types";
import {
  HIGH_DEMAND_UNIQUE_MIN,
  MAP_CATEGORIES,
  SEVERE_DEFICIT_MIN,
  buildMapPoints,
  loadGeoCoordinates,
  type GeoCoordinateCatalog,
  type MapCategory,
  type MapPoint,
} from "@/lib/geoMap";
import { formatCr, formatImpact } from "@/lib/format";
import DistrictMap from "./DistrictMap";

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

export default function GeoMapPanel({
  data,
  budget,
  equityMode,
  scenario,
  onBudget,
  onEquityMode,
}: {
  data: DashboardPayload;
  budget: number;
  equityMode: string;
  scenario: ScenarioResult | undefined;
  onBudget: (budget: number) => void;
  onEquityMode: (mode: string) => void;
}) {
  const [catalog, setCatalog] = useState<GeoCoordinateCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [categories, setCategories] = useState<MapCategory[]>([...MAP_CATEGORIES]);
  const [selectionFilter, setSelectionFilter] = useState<"all" | "selected">("all");
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    loadGeoCoordinates()
      .then(setCatalog)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Could not load demo coordinates.");
      });
  }, []);

  const points = useMemo(() => {
    if (!catalog) return [];
    return buildMapPoints(data, catalog.locations, scenario?.selected_ids ?? []);
  }, [catalog, data, scenario?.selected_ids]);

  const visible = useMemo(() => {
    return points.filter((point) => {
      if (!categories.includes(point.category)) return false;
      if (selectionFilter === "selected" && !point.selected) return false;
      return true;
    });
  }, [points, categories, selectionFilter]);

  const active = visible.find((point) => point.id === activeId) ?? null;

  function toggleCategory(category: MapCategory) {
    setCategories((current) => {
      if (current.includes(category)) {
        const next = current.filter((item) => item !== category);
        return next.length ? next : current;
      }
      return [...current, category];
    });
  }

  const modes = [
    { id: "maximum_impact", label: "Maximum impact / no equity constraint" },
    { id: "equity_25", label: "25% underserved impact" },
    { id: "equity_30", label: "30% underserved impact" },
    { id: "equity_40", label: "40% underserved impact" },
  ];

  return (
    <section>
      <div className="page-head">
        <div>
          <h2>Geospatial view</h2>
          <p>
            Synthetic district schematic of demand and candidate projects. Marker
            selection follows the same exported Policy Simulator scenario.
          </p>
        </div>
      </div>

      <div className="callout mock-note">
        Demo coordinates only. This is a fictional CivicPrior district layout,
        not official administrative geography and not a live basemap.
      </div>

      <div className="controls">
        <label>
          Budget
          <select
            value={budget}
            onChange={(event) => onBudget(Number(event.target.value))}
          >
            {data.meta.available_budgets_cr.map((value) => (
              <option key={value} value={value}>
                {formatCr(value)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Equity mode
          <select
            value={equityMode}
            onChange={(event) => onEquityMode(event.target.value)}
          >
            {modes.map((mode) => (
              <option key={mode.id} value={mode.id}>
                {mode.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Projects
          <select
            value={selectionFilter}
            onChange={(event) =>
              setSelectionFilter(event.target.value as "all" | "selected")
            }
          >
            <option value="all">All projects</option>
            <option value="selected">Selected only</option>
          </select>
        </label>
      </div>

      <div className="filter-row">
        {MAP_CATEGORIES.map((category) => (
          <button
            key={category}
            type="button"
            className={`filter-chip ${categories.includes(category) ? "on" : ""} ${category}`}
            onClick={() => toggleCategory(category)}
          >
            {category}
          </button>
        ))}
      </div>

      {scenario ? (
        <div className="kpis">
          <article className="card">
            <div className="label">Selected</div>
            <div className="value">{scenario.selected.length}</div>
          </article>
          <article className="card">
            <div className="label">Total cost</div>
            <div className="value">{formatCr(scenario.total_cost)}</div>
          </article>
          <article className="card">
            <div className="label">Service impact</div>
            <div className="value">{formatImpact(scenario.total_impact)}</div>
          </article>
          <article className="card">
            <div className="label">Map points</div>
            <div className="value">{visible.length}</div>
            <div className="hint">Filters hide markers only</div>
          </article>
        </div>
      ) : (
        <p className="error">No exported scenario for this budget and equity mode.</p>
      )}

      {error ? <p className="error">{error}</p> : null}
      {!catalog && !error ? <p className="muted">Loading demo coordinates…</p> : null}

      <div className="geo-layout">
        <div className="card geo-map-card">
          {catalog ? (
            <DistrictMap
              points={visible}
              activeId={active?.id ?? null}
              onSelect={setActiveId}
            />
          ) : null}
          <ul className="map-legend">
            <li>
              <span className="swatch selected" /> Selected project
            </li>
            <li>
              <span className="swatch unselected" /> Unselected / rejected
            </li>
            <li>
              <span className="swatch underserved" /> Underserved geography
            </li>
            <li>
              <span className="swatch deficit" /> Severe deficit (≥ {SEVERE_DEFICIT_MIN})
            </li>
            <li>Larger marker = high demand (≥ {HIGH_DEMAND_UNIQUE_MIN} unique requests)</li>
            <li>
              <span className="swatch water" /> Water
            </li>
            <li>
              <span className="swatch healthcare" /> Healthcare
            </li>
            <li>
              <span className="swatch roads" /> Roads
            </li>
          </ul>
        </div>

        <aside className="card geo-detail">
          <h3>Location detail</h3>
          {active ? <PointDetail point={active} /> : (
            <p className="muted">Select a marker to inspect demand and project status.</p>
          )}
        </aside>
      </div>
    </section>
  );
}

function PointDetail({ point }: { point: MapPoint }) {
  return (
    <>
      {point.selected ? (
        <div className="callout ok">Selected in the current scenario</div>
      ) : (
        <div className="callout tradeoff">
          {point.unmatched ? "Demand cluster with no linked project" : "Rejected in the current scenario"}
        </div>
      )}
      <dl className="snapshot-list interpretation-list">
        <Field label="Project">{point.project_name ?? "None"}</Field>
        <Field label="Location">{point.location}</Field>
        <Field label="Category">{point.category}</Field>
        <Field label="Need score">{point.need_score == null ? "n/a" : point.need_score.toFixed(2)}</Field>
        <Field label="Expected impact">
          {point.expected_impact == null ? "n/a" : formatImpact(point.expected_impact)}
        </Field>
        <Field label="Cost">{point.cost_cr == null ? "n/a" : formatCr(point.cost_cr)}</Field>
        <Field label="Equity">{point.equity_score.toFixed(1)}</Field>
        <Field label="Unique requests">{point.unique_requests}</Field>
        <Field label="Request density">{point.request_density.toFixed(3)} / 1,000</Field>
        <Field label="Infrastructure deficit">{point.infrastructure_deficit.toFixed(1)}</Field>
        <Field label="Active investment">{formatCr(point.active_investment)}</Field>
        <Field label="Investment gap">{point.investment_gap.toFixed(0)}</Field>
        <Field label="Citizen demand">{point.citizen_demand_summary}</Field>
        <Field label="Status">
          {point.selected ? "selected" : point.unmatched ? "unmatched demand" : "rejected"}
        </Field>
      </dl>
    </>
  );
}
