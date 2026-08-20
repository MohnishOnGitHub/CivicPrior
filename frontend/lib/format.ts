export function formatInt(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

export function formatImpact(value: number): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatCr(value: number): string {
  return `₹${value.toLocaleString("en-US", { maximumFractionDigits: 0 })} Cr`;
}

export function formatShare(value: number | null | undefined): string {
  if (value == null) return "n/a";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatSacrificed(value: number | null | undefined): string {
  if (value == null) return "n/a";
  return `${value.toFixed(2)}%`;
}

export function formatDelta(value: number | null | undefined, digits = 2): string {
  if (value == null) return "n/a";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

export function tradeoffSentence(args: {
  impact_sacrificed_pct: number | null;
  underserved_impact_share_baseline: number | null;
  underserved_impact_share_selected: number | null;
}): string {
  const from = formatShare(args.underserved_impact_share_baseline);
  const to = formatShare(args.underserved_impact_share_selected);
  const sacrificed = formatSacrificed(args.impact_sacrificed_pct);
  const baselineShare = args.underserved_impact_share_baseline ?? 0;
  const selectedShare = args.underserved_impact_share_selected ?? 0;
  const direction =
    selectedShare > baselineShare
      ? "increase"
      : selectedShare < baselineShare
        ? "decrease"
        : "hold";
  return `This scenario sacrifices ${sacrificed} aggregate expected impact to ${direction} underserved impact share from ${from} to ${to}.`;
}

export function findScenario(
  scenarios: Array<{ budget_cr: number; equity_mode: string }>,
  budget: number,
  equityMode: string,
) {
  return scenarios.find(
    (scenario) => scenario.budget_cr === budget && scenario.equity_mode === equityMode,
  );
}
