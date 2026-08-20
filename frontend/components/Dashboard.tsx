"use client";

import { useEffect, useMemo, useState } from "react";
import { loadDashboard } from "@/lib/loadDashboard";
import { findScenario } from "@/lib/format";
import type { DashboardPayload, ScenarioResult, ViewId } from "@/lib/types";
import OverviewPanel from "./OverviewPanel";
import DemandPanel from "./DemandPanel";
import SimulatorPanel from "./SimulatorPanel";
import ComparePanel from "./ComparePanel";
import IntakePanel from "./IntakePanel";

const NAV: Array<{ id: ViewId; label: string; hero?: boolean }> = [
  { id: "intake", label: "Citizen intake" },
  { id: "overview", label: "Overview" },
  { id: "demand", label: "Demand intelligence" },
  { id: "simulator", label: "Policy simulator", hero: true },
  { id: "compare", label: "Scenario comparison" },
];

export default function Dashboard() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewId>("simulator");
  const [budget, setBudget] = useState(60);
  const [equityMode, setEquityMode] = useState("equity_30");

  useEffect(() => {
    loadDashboard()
      .then((payload) => {
        setData(payload);
        setBudget(payload.meta.default_budget_cr);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load dashboard data");
      });
  }, []);

  const selected = useMemo(
    () =>
      data
        ? (findScenario(data.scenarios, budget, equityMode) as ScenarioResult | undefined)
        : undefined,
    [data, budget, equityMode],
  );
  const baseline = useMemo(
    () =>
      data
        ? (findScenario(data.scenarios, budget, "maximum_impact") as
            | ScenarioResult
            | undefined)
        : undefined,
    [data, budget],
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <h1>CivicPrior</h1>
          <p>Decision intelligence · v0.1</p>
        </div>
        <nav className="nav">
          {NAV.map((item) => (
            <button
              key={item.id}
              className={`${view === item.id ? "active" : ""} ${item.hero ? "hero-nav" : ""}`}
              onClick={() => setView(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <p className="sidebar-note">
          {data
            ? `Catalog: ${data.catalog.replace(/_/g, " ")}. Optimizer results are imported, not computed in the browser.`
            : "Citizen intake uses a local mock extractor. Gemini is not called."}
        </p>
      </aside>
      <main className="main">
        <p className="data-note">
          Synthetic demonstration data · not official government statistics
        </p>
        {view === "intake" ? <IntakePanel /> : null}
        {view !== "intake" && error ? <p className="error">{error}</p> : null}
        {view !== "intake" && !data && !error ? (
          <p className="loading">Loading CivicPrior decision export…</p>
        ) : null}
        {data && view === "overview" ? <OverviewPanel data={data} /> : null}
        {data && view === "demand" ? <DemandPanel data={data} /> : null}
        {data && view === "simulator" ? (
          <SimulatorPanel
            data={data}
            budget={budget}
            equityMode={equityMode}
            scenario={selected}
            baseline={baseline}
            onBudget={setBudget}
            onEquityMode={setEquityMode}
          />
        ) : null}
        {data && view === "compare" ? (
          <ComparePanel baseline={baseline} selected={selected} />
        ) : null}
      </main>
    </div>
  );
}
