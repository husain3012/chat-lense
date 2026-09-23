"use client";
import type { ChatReport, Finding } from "@/lib/report-types";
import type { Person } from "@/lib/types";

export function WhoDoesWhat({
  data,
  people,
  onEvidence,
}: {
  data: NonNullable<ChatReport["behaviors"]>;
  people: Person[];
  onEvidence: (finding: Finding) => void;
}) {
  function evidence(title: string, description: string, ids: string[]) {
    onEvidence({
      id: "behavior",
      family: "behavior",
      title,
      description,
      category: "Who does what?",
      section: "deep",
      value: "",
      label: "",
      participant_ids: [],
      facts: [],
      evidence_ids: ids,
      evidence_total: ids.length,
      method:
        "AI-classified messages. One count per message per category; nearby context is considered.",
      caveat:
        "Classification can miss context or sarcasm. These are expressions in messages, not personal traits.",
      visual_type: "none",
      visual: [],
      interpretation: true,
      source: "ai",
    });
  }
  return (
    <section
      id="who-does-what"
      className="my-12 rounded-3xl border border-border p-6 md:p-9 bg-surface"
    >
      <p className="text-accent text-sm font-semibold uppercase tracking-widest">
        The little things that make you, you
      </p>
      <h2 className="text-3xl font-bold mt-3 mb-3">Who does what? 👀</h2>
      <p className="text-secondary text-sm mb-6">
        Gemini tagged {data.processed.toLocaleString()} /{" "}
        {data.total.toLocaleString()} messages across the chat.
        {data.version !== 1 &&
          " Still reading — these comparisons are provisional."}{" "}
        Counts describe messages, not who loves more, who is to blame, or
        anyone’s actual sex drive.
      </p>
      <div className="divide-y divide-border">
        {Object.entries(data.definitions).map(([key, definition]) => {
          const counts = data.categories?.[key] || {};
          const ranked = people
            .map((p) => ({ ...p, count: counts[p.id]?.count || 0 }))
            .sort((a, b) => b.count - a.count);
          const max = Math.max(1, ranked[0]?.count || 0);
          const tied =
            ranked.length > 1 && ranked[0].count === ranked[1].count && max > 1;
          return (
            <details key={key} className="py-4">
              <summary className="cursor-pointer font-semibold">
                {definition.title}
                <span className="block text-xs text-secondary font-normal mt-1">
                  {max === 1 && !ranked.some((p) => p.count)
                    ? "No clear examples found"
                    : tied
                      ? "Same count at the top"
                      : `${ranked[0]?.count || 0} tagged messages at the top`}{" "}
                  · Expand comparison
                </span>
              </summary>
              <p className="text-sm text-secondary my-3">
                {definition.description}
              </p>
              {ranked.map((person) => (
                <div key={person.id} className="my-3">
                  <div className="flex justify-between gap-3 text-sm">
                    <span>
                      {person.display_name}
                      {person.is_current_user ? " (you)" : ""}
                    </span>
                    <span>{person.count.toLocaleString()} messages{data.participant_messages?.[person.id] ? ` · ${(100 * person.count / data.participant_messages[person.id]).toFixed(1)} per 100` : ""}</span>
                  </div>
                  <div className="h-2 rounded-full bg-border my-2 overflow-hidden">
                    <div
                      className="h-full bg-accent rounded-full transition-all duration-700"
                      style={{ width: `${(100 * person.count) / max}%` }}
                    />
                  </div>
                  {!!counts[person.id]?.evidence_ids.length && (
                    <button
                      className="text-xs text-accent"
                      onClick={() =>
                        evidence(
                          definition.title,
                          definition.description,
                          counts[person.id].evidence_ids,
                        )
                      }
                    >
                      See examples from {person.display_name} ↗
                    </button>
                  )}
                </div>
              ))}
              <p className="text-xs text-secondary">
                One count per tagged message, not per word or incident. More
                prolific texters have more opportunities to appear here. Zero
                means none identified.
              </p>
            </details>
          );
        })}
      </div>
      <h3 className="text-xl font-semibold mt-8 mb-2">
        Their happy rabbit holes 🐇
      </h3>
      <p className="text-sm text-secondary mb-4">
        Interests they explicitly expressed — topic labels may overlap.
      </p>
      <div className="grid gap-5 md:grid-cols-2">
        {people.map((person) => {
          const topics = Object.entries(data.interests || {})
            .filter(([, counts]) => counts[person.id])
            .sort((a, b) => b[1][person.id].count - a[1][person.id].count)
            .slice(0, 8);
          return (
            <div key={person.id}>
              <h4 className="font-semibold mb-3">{person.display_name}</h4>
              <div className="flex flex-wrap gap-2">
                {topics.length ? (
                  topics.map(([topic, counts]) => (
                    <button
                      key={topic}
                      className="rounded-full border border-border px-3 py-2 text-sm hover:text-accent"
                      onClick={() =>
                        evidence(
                          `${person.display_name} · ${topic}`,
                          "An explicitly expressed interest, classified by Gemini.",
                          counts[person.id].evidence_ids,
                        )
                      }
                    >
                      {topic} · {counts[person.id].count} ↗
                    </button>
                  ))
                ) : (
                  <p className="text-sm text-secondary">
                    No clear interests identified yet.
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-secondary mt-6">
        AI classification can miss sarcasm and context. Open the original
        conversation to judge an example.{" "}
        {data.truncated
          ? `${data.truncated.toLocaleString()} long messages were limited to their first 1,024 characters for this pass.`
          : ""}
      </p>
    </section>
  );
}
