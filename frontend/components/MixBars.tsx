import type { Mix } from "@/lib/types";
import { formatCr } from "@/lib/format";

export function MixBars({ mix, unit = "count" }: { mix: Mix; unit?: string }) {
  const entries = Object.entries(mix);
  const max = Math.max(...entries.map(([, value]) => value), 1);
  return (
    <div className="mix">
      {entries.map(([key, value]) => (
        <div className="mix-row" key={key}>
          <span>{key}</span>
          <div className="bar">
            <span style={{ width: `${(value / max) * 100}%` }} />
          </div>
          <span>
            {value}
            {unit === "cr" ? " Cr" : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

export function CategoryMix({
  counts,
  spend,
}: {
  counts: Mix;
  spend?: Mix;
}) {
  const categories = Array.from(
    new Set([...Object.keys(counts), ...Object.keys(spend ?? {})]),
  ).sort();
  if (!categories.length) {
    return <p className="muted">No selected projects.</p>;
  }
  const maxSpend = Math.max(...categories.map((category) => spend?.[category] ?? 0), 1);
  const maxCount = Math.max(...categories.map((category) => counts[category] ?? 0), 1);

  return (
    <div className="category-mix">
      {categories.map((category) => {
        const count = counts[category] ?? 0;
        const amount = spend?.[category] ?? 0;
        return (
          <div className="category-mix-row" key={category}>
            <div className="category-mix-label">{category}</div>
            <div className="category-mix-metrics">
              <span>
                {count} {count === 1 ? "project" : "projects"}
              </span>
              {spend ? <span>{formatCr(amount)}</span> : null}
            </div>
            <div className="bar" title={spend ? "Share of selected spend" : "Share of selected projects"}>
              <span
                style={{
                  width: `${((spend ? amount : count) / (spend ? maxSpend : maxCount)) * 100}%`,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
