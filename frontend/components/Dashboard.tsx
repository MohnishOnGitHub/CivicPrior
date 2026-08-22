"use client";

import { useEffect, useMemo, useState } from "react";
import { loadDashboard } from "@/lib/loadDashboard";
import { findScenario } from "@/lib/format";
import type { DashboardPayload, ScenarioResult, ViewId } from "@/lib/types";
import OverviewPanel from "./OverviewPanel";
import DemandPanel from "./DemandPanel";
import SimulatorPanel from "./SimulatorPanel";
import ComparePanel from "./ComparePanel";
import GeoMapPanel from "./GeoMapPanel";
import ImpactPanel from "./ImpactPanel";
import IntakePanel from "./IntakePanel";
import BricsPanel from "./BricsPanel";
import DemoGuide from "./DemoGuide";

const NAV: Array<{ id: ViewId; label: string; hero?: boolean }> = [
  { id: "intake", label: "Citizen intake" },
  { id: "demand", label: "Demand intelligence" },
  { id: "geospatial", label: "Geospatial view" },
  { id: "simulator", label: "Policy simulator", hero: true },
  { id: "compare", label: "Scenario comparison" },
  { id: "impact", label: "Impact tracking" },
  { id: "brics", label: "BRICS / Digital Public Good" },
  { id: "overview", label: "Overview" },
];

export default function Dashboard() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewId>("intake");
  const [budget, setBudget] = useState(60);
  const [equityMode, setEquityMode] = useState("equity_30");
  const [showDemoGuide, setShowDemoGuide] = useState(true);

  function goDemoStep(next: ViewId) {
    if (next === "simulator" || next === "compare" || next === "geospatial") {
      setBudget(60);
      setEquityMode("equity_30");
    }
    setView(next);
  }

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
        <button
          type="button"
          className="demo-toggle"
          onClick={() => setShowDemoGuide((open) => !open)}
        >
          {showDemoGuide ? "Hide demo guide" : "Show demo guide"}
        </button>
        <p className="sidebar-note">
          {data
            ? `Catalog: ${data.catalog.replace(/_/g, " ")}. Optimizer results are imported, not computed in the browser.`
            : "Citizen intake calls a server route. Gemini stays server-side."}
        </p>
      </aside>
      <main className="main">
        <p className="data-note">
          Synthetic demonstration data · not official government statistics
        </p>
        {showDemoGuide ? (
          <DemoGuide
            data={data}
            view={view}
            onGo={goDemoStep}
            onClose={() => setShowDemoGuide(false)}
          />
        ) : null}
        {view === "intake" ? <IntakePanel /> : null}
        {view === "impact" ? <ImpactPanel /> : null}
        {view === "brics" ? <BricsPanel /> : null}
        {view !== "intake" && view !== "impact" && view !== "brics" && error ? (
          <p className="error">{error}</p>
        ) : null}
        {view !== "intake" &&
        view !== "impact" &&
        view !== "brics" &&
        !data &&
        !error ? (
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
        {data && view === "geospatial" ? (
          <GeoMapPanel
            data={data}
            budget={budget}
            equityMode={equityMode}
            scenario={selected}
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
