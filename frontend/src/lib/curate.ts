import type { Finding } from "./report-types";

// Reserve twelve of the fifty story slots for timeline chapters.
export function curate(findings: Finding[], limit = 38): Finding[] {
  const selected: Finding[] = [];
  const families = new Set<string>();
  const titles = new Set<string>();
  const kinds = new Map<string, number>();
  let aiCount = 0;
  const ranked = findings
    .slice()
    .sort(
      (a, b) =>
        (b.display_score ?? b.score ?? 0) - (a.display_score ?? a.score ?? 0),
    );
  for (const finding of ranked) {
    if (
      finding.source === "ai" &&
      ((finding.display_score ?? finding.score ?? 0) < 7 ||
        aiCount >= 24 ||
        (kinds.get(finding.moment_kind || "connection") || 0) >= 4)
    )
      continue;
    const title = finding.title.toLocaleLowerCase().trim();
    if (families.has(finding.family) || titles.has(title)) continue;
    if (
      selected.some(
        (old) =>
          old.evidence_ids.length > 0 &&
          finding.evidence_ids.length > 0 &&
          old.evidence_ids.filter((id) => finding.evidence_ids.includes(id))
            .length /
            Math.min(old.evidence_ids.length, finding.evidence_ids.length) >
            0.8,
      )
    )
      continue;
    selected.push(finding);
    if (finding.source === "ai") {
      aiCount++;
      const kind = finding.moment_kind || "connection";
      kinds.set(kind, (kinds.get(kind) || 0) + 1);
    }
    families.add(finding.family);
    titles.add(title);
    if (selected.length >= limit) break;
  }
  return selected;
}
