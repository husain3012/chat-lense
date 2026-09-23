import type { Era, Finding } from "@/lib/report-types";
import { ArrowUpRight } from "lucide-react";
export function Timeline({
  periods,
  onEvidence,
}: {
  periods: Era[];
  onEvidence: (f: Finding) => void;
}) {
  const max = Math.max(1, ...periods.map((p) => p.message_count));
  return (
    <div className="space-y-4">
      {periods.map((p, i) => (
        <article key={p.period} className="era-card">
          <div className="flex gap-5">
            <div className="hidden sm:flex flex-col items-center shrink-0">
              <span className="w-9 h-9 rounded-full bg-accent/10 text-accent flex items-center justify-center text-xs font-semibold">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="w-px flex-1 bg-border mt-3" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-center gap-3">
                <p className="eyebrow">
                  {new Date(p.period + "-01T00:00:00Z").toLocaleDateString(
                    undefined,
                    { month: "long", year: "numeric", timeZone: "UTC" },
                  )}
                </p>
                {p.partial && <span className="badge">Partial month</span>}
              </div>
              <h3 className="text-xl font-medium mt-3">{p.title}</h3>
              <p className="text-sm leading-relaxed text-secondary mt-2">
                {p.summary}
              </p>
              <div className="h-2 bg-muted rounded-full mt-5">
                <div
                  className="h-2 bg-accent/60 rounded-full"
                  style={{ width: `${(p.message_count / max) * 100}%` }}
                />
              </div>
              <div className="flex flex-wrap gap-4 text-[11px] text-secondary mt-3">
                <span>{p.late_share.toFixed(0)}% late-night</span>
                <span>{p.weekend_share.toFixed(0)}% weekend</span>
                <span>{p.average_length.toFixed(0)} characters / text</span>
                <button
                  className="ml-auto inline-flex items-center gap-1 text-accent"
                  onClick={() =>
                    onEvidence({
                      id: "era-" + p.period,
                      family: "era",
                      category: "Timeline",
                      section: "timeline",
                      title: p.title,
                      description: p.summary,
                      value: p.period,
                      label: "Month",
                      participant_ids: [],
                      facts: [],
                      evidence_ids: p.evidence_ids,
                      evidence_total: p.message_count,
                      method:
                        "Local calendar-month activity. Opening and closing partial months are labelled and excluded from change comparisons. Era names describe measured activity, not inferred causes.",
                      caveat: null,
                      visual_type: "none",
                      visual: [],
                      interpretation: false,
                      source: "measured",
                    })
                  }
                >
                  View moments
                  <ArrowUpRight size={12} />
                </button>
              </div>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
