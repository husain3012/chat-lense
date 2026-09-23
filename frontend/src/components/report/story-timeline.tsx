"use client";
import { useState } from "react";
import type { Finding } from "@/lib/report-types";
export type StoryCover = {
  title: string;
  subtitle: string;
  emoji: string;
  eras: {
    title: string;
    summary: string;
    period: string;
    moment_ids: string[];
    kind?: string;
  }[];
};
export function StoryTimeline({
  cover,
  moments,
  onEvidence,
}: {
  cover?: StoryCover | null;
  moments: Finding[];
  onEvidence: (f: Finding) => void;
}) {
  const [selectedPeriod, setSelectedPeriod] = useState<string | null>(null);
  const [selectedChapter, setSelectedChapter] = useState(0);
  const chapters = cover?.eras?.length
    ? cover.eras
    : moments
        .filter((m) => m.source_quotes?.length)
        .slice()
        .sort((a, b) =>
          a.source_quotes![0].timestamp.localeCompare(
            b.source_quotes![0].timestamp,
          ),
        )
        .filter(
          (_, i, all) => i % Math.max(1, Math.ceil(all.length / 12)) === 0,
        )
        .map((m) => ({
          title: m.title,
          summary: m.description,
          period: m.source_quotes![0].timestamp.slice(0, 7),
          moment_ids: [m.id],
          kind: m.moment_kind || "chapter",
        }));
  if (!chapters.length) return null;
  const periods = [...new Set(chapters.map((c) => c.period))].sort();
  const first = Date.parse(periods[0] + "-01");
  const span = Math.max(
    1,
    Date.parse(periods[periods.length - 1] + "-01") - first,
  );
  const monthGaps = periods
    .slice(1)
    .map((p, i) => Date.parse(p + "-01") - Date.parse(periods[i] + "-01"));
  const width = Math.max(
    640,
    monthGaps.length ? (span / Math.min(...monthGaps)) * 110 + 90 : 640,
  );
  const position = (period: string) =>
    45 + ((Date.parse(period + "-01") - first) / span) * (width - 90);
  const shown = selectedPeriod
    ? chapters.filter((c) => c.period === selectedPeriod)
    : chapters;
  return (
    <>
      <p className="prose-note mb-3">
        Every chat has chapters. Follow the thread, then step back into the
        exchanges that made each one memorable.
      </p>
      <div
        className="overflow-x-auto rounded-2xl border border-border bg-surface"
        aria-label="Dated conversation event graph"
      >
        <div className="relative" style={{ width, height: 142 }}>
          <svg width={width} height="142" aria-hidden="true">
            <line
              x1="45"
              y1="58"
              x2={width - 45}
              y2="58"
              stroke="currentColor"
              opacity=".2"
              strokeWidth="3"
            />
            {periods.map((p) => (
              <line
                key={p}
                x1={position(p)}
                x2={position(p)}
                y1="58"
                y2="103"
                stroke="currentColor"
                opacity=".2"
                strokeDasharray="3 4"
              />
            ))}
          </svg>
          {periods.map((period) => {
            const events = chapters.filter((c) => c.period === period);
            const tense = events.some((c) => c.kind === "tension");
            const repaired = events.some((c) => c.kind === "repair");
            return (
              <button
                key={period}
                aria-pressed={selectedPeriod === period}
                aria-label={`${period}: ${events.length} story events`}
                onClick={() => {
                  setSelectedPeriod(selectedPeriod === period ? null : period);
                  setSelectedChapter(0);
                }}
                className="absolute -translate-x-1/2 flex flex-col items-center gap-3 text-xs"
                style={{ left: position(period), top: 36 }}
              >
                <span
                  className={`w-11 h-11 rounded-full border-2 flex items-center justify-center text-lg transition-transform hover:scale-110 ${selectedPeriod === period ? "border-accent bg-accent/20 scale-110 shadow-lg" : "border-border bg-surface"}`}
                >
                  {tense ? "🌧️" : repaired ? "🌤️" : "✨"}
                </span>
                <time>
                  {new Date(period + "-01T00:00:00Z").toLocaleDateString("en", {
                    month: "short",
                    year: "numeric",
                    timeZone: "UTC",
                  })}
                </time>
                <span className="text-secondary">
                  {events.length} {events.length === 1 ? "moment" : "moments"}
                </span>
              </button>
            );
          })}
        </div>
      </div>
      {selectedPeriod && (
        <button
          className="text-xs text-accent mt-3"
          onClick={() => {
            setSelectedPeriod(null);
            setSelectedChapter(0);
          }}
        >
          Show the whole story ×
        </button>
      )}
      <div className="flex items-center justify-between mt-6 mb-3">
        <button
          className="text-sm text-accent disabled:opacity-30"
          disabled={selectedChapter === 0}
          onClick={() => setSelectedChapter((i) => i - 1)}
        >
          ← Previous chapter
        </button>
        <span className="text-xs text-secondary">
          {Math.min(selectedChapter + 1, shown.length)} / {shown.length}
        </span>
        <button
          className="text-sm text-accent disabled:opacity-30"
          disabled={selectedChapter >= shown.length - 1}
          onClick={() => setSelectedChapter((i) => i + 1)}
        >
          Next chapter →
        </button>
      </div>
      <div aria-label="Conversation story timeline">
        {shown.slice(selectedChapter, selectedChapter + 1).map((chapter, i) => (
          <article
            className="rounded-3xl border border-accent/30 bg-accent/10 p-6 sm:p-8"
            key={chapter.title}
          >
            <div className="story-dot">
              {["🌱", "✨", "🌀", "🌤️", "🎞️"][i % 5]}
            </div>
            <time className="eyebrow">{chapter.period}</time>
            <h3 className="text-xl mt-3">{chapter.title}</h3>
            <p className="text-sm text-secondary leading-relaxed mt-3">
              {chapter.summary}
            </p>
            <div className="flex flex-wrap gap-2 mt-4">
              {chapter.moment_ids.map((mid) => {
                const m = moments.find((f) => f.id === mid);
                return (
                  m && (
                    <button
                      className="text-xs text-accent"
                      key={mid}
                      onClick={() => onEvidence(m)}
                    >
                      Revisit {m.title} ↗
                    </button>
                  )
                );
              })}
            </div>
            <p className="prose-note mt-3">
              Gemini interpretation · linked evidence
            </p>
          </article>
        ))}
      </div>
    </>
  );
}
