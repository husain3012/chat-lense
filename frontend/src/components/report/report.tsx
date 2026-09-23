"use client";
import { useEffect, useState } from "react";
import { ArrowDown, ShieldCheck } from "lucide-react";
import { api, number } from "@/lib/api";
import type { Person } from "@/lib/types";
import type { ChatReport, Finding, Tone } from "@/lib/report-types";
import { Button } from "@/components/ui/button";
import { FindingCard } from "./finding-card";
import { Evidence } from "./conversation-reader";
import { Timeline } from "./timeline";
import { ThinkingOrb } from "thinking-orbs";
import { ChatContext } from "./chat-context";
import { AskChat } from "./ask-chat";
import { StoryTimeline } from "./story-timeline";
import { curate } from "@/lib/curate";
import { momentCategories } from "@/lib/moment-categories";
import { ReplyNetwork } from "./reply-network";
import { WhoDoesWhat } from "./who-does-what";
import { ExportWrap } from "./export-wrap";
type Job = {
  status: string;
  ai_enabled?: boolean;
  error?: string;
  progress: {
    processed?: number;
    total?: number;
    calls?: number;
    stage?: string;
    last_batch_messages?: number;
    last_batch_seconds?: number;
  };
};

export function ReportView({
  id,
  people,
  group,
  sourceTimezone,
}: {
  id: string;
  people: Person[];
  group: boolean;
  sourceTimezone?: string;
}) {
  const [report, setReport] = useState<ChatReport | null>(null);
  const [tone, setTone] = useState<Tone>("fun");
  const [ready, setReady] = useState(false);
  const [gap, setGap] = useState("4");
  const [zone, setZone] = useState("UTC");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [evidence, setEvidence] = useState<Finding | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [asking, setAsking] = useState<{ finding?: Finding } | null>(null);
  const [momentFilter, setMomentFilter] = useState("all");
  const [aiError, setAiError] = useState("");
  const [exporting, setExporting] = useState(false);
  const synthesizing =
    !!job && ["queued", "running", "retry"].includes(job.status);
  const queued = job?.status === "queued";
  useEffect(() => {
    const saved = localStorage.getItem("chatlens-tone");
    setTone(saved === "balanced" || saved === "analytical" ? saved : "fun");
    setGap(localStorage.getItem("chatlens-gap") || "4");
    setZone(
      sourceTimezone || localStorage.getItem("chatlens-timezone") || "UTC",
    );
    setReady(true);
  }, [sourceTimezone]);
  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setAiError("");
    api<ChatReport | { pending: true }>(
      `/conversations/${id}/report?${new URLSearchParams({ tone, session_gap: gap, timezone: zone, queued: "true" })}`,
      { signal: controller.signal },
    )
      .then((result) => {
        if (!("pending" in result)) {
          setReport(result);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          setError(e.message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [id, tone, gap, zone, ready]);
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    let lastRevision = "";
    async function poll() {
      try {
        const next = await api<Job>(`/conversations/${id}/analysis`);
        if (stopped) return;
        setAiError("");
        setJob(next);
        const revision = `${next.status}:${next.progress.processed}:${next.progress.calls}`;
        if (revision !== lastRevision && next.status !== "not_started") {
          lastRevision = revision;
          const updated = await api<ChatReport | { pending: true }>(
            `/conversations/${id}/report?${new URLSearchParams({ tone, session_gap: gap, timezone: zone, queued: "true" })}`,
          );
          if (!stopped && !("pending" in updated)) {
            setReport(updated);
            setLoading(false);
            setError("");
          }
        }
        if (next.status === "completed") return;
        if (
          !stopped &&
          next.status !== "not_started" &&
          next.status !== "failed"
        )
          timer = setTimeout(poll, 5000);
      } catch {
        if (!stopped) {
          setAiError(
            "Connection interrupted. Reconnecting to saved server progress…",
          );
          timer = setTimeout(poll, 10000);
        }
      }
    }
    void poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [id, queued, tone, gap, zone]);
  async function enqueue(refresh = false) {
    setAiError("");
    try {
      const next = await api<Job>(`/conversations/${id}/analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent: true, refresh }),
      });
      setJob(next);
    } catch (e) {
      setAiError((e as Error).message);
    }
  }
  if (loading)
    return (
      <div
        className="discovery-card py-16 flex flex-col items-center"
        role="status"
      >
        <ThinkingOrb state="weaving" size={64} />
        <h2 className="text-lg">Looking for the little things.</h2>
        <p className="text-secondary text-sm mt-2">
          Comparing habits, turns, rhythms, and changes across your chat…
        </p>
        <p className="prose-note mt-3">
          Queued on the server. You can close this page.
        </p>
        {job?.status === "failed" && (
          <>
            <p role="alert">{job.error}</p>
            <Button onClick={() => void enqueue()}>Resume analysis</Button>
          </>
        )}
      </div>
    );
  if (error || !report)
    return (
      <div className="card text-sm" role="alert">
        {error || "Report unavailable."}{" "}
        <span className="text-secondary">
          Your messages and statistics are still available in the other tabs.
        </span>
      </div>
    );
  const allFindings = [
    ...report.insights,
    ...(report.synthesis?.insights || []),
  ];
  const selected = curate(allFindings);
  const measured = selected.filter((i) => i.source !== "ai");
  const top = measured.filter((i) => i.section === "top");
  const micro = measured.filter((i) => i.section === "micro");
  const cards = measured.filter((i) => i.section === "participants");
  const pair = measured.filter((i) => i.section === "pairs");
  const awards = measured.filter((i) => i.section === "superlatives");
  const topics = measured.filter((i) => i.section === "topics");
  const deep = measured.filter((i) => i.section === "deep");
  const ai = selected.filter((i) => i.source === "ai");
  const visibleMoments =
    momentFilter !== "all"
      ? ai.filter((i) => i.moment_kind === momentFilter)
      : ai;
  const render = (items: Finding[], compact = false) =>
    items.map((i) => (
      <FindingCard
        key={i.id}
        finding={i}
        onEvidence={setEvidence}
        title={report.title}
        compact={compact}
      />
    ));
  return (
    <ChatContext.Provider
      value={{
        me: people.find((p) => p.is_current_user)?.id,
        meName: people.find((p) => p.is_current_user)?.display_name,
        ask: (finding) => setAsking({ finding }),
      }}
    >
      <div className="report-space scrapbook">
        {exporting && (
          <ExportWrap
            id={id}
            report={report}
            findings={selected}
            onClose={() => setExporting(false)}
          />
        )}
        <section
          className="synthesis-panel"
          aria-label="Server analysis progress"
        >
          <div className="flex gap-5 items-center">
            {synthesizing && (
              <ThinkingOrb
                state={job?.status === "retry" ? "breathing" : "weaving"}
                size={64}
              />
            )}
            <div>
              <h3 className="text-lg font-semibold" role="status">
                {synthesizing
                  ? "Finding the story between the lines…"
                  : job?.status === "completed"
                    ? "Your story is ready ✨"
                    : job?.status === "failed"
                      ? "Analysis paused · resume when you’re ready"
                      : "Let’s look a little closer"}
              </h3>
              <p className="prose-note mt-2">
                {job?.progress.processed || 0} /{" "}
                {job?.progress.total || report.snapshot.messages} messages read
                · {job?.progress.calls || 0} calls
              </p>
              {synthesizing && (
                <p className="prose-note mt-2">
                  {job?.progress.stage && (
                    <span className="block mb-1">{job.progress.stage}</span>
                  )}
                  You can close this page. Analysis continues on the server,
                  saving each passage as it goes. Large chats can take hours.
                </p>
              )}
              {!!job?.progress.last_batch_messages && (
                <p className="prose-note mt-2">
                  Last passage:{" "}
                  {job.progress.last_batch_messages.toLocaleString()} new
                  messages in {job.progress.last_batch_seconds}s. Batch size
                  adapts to message length.
                </p>
              )}
              {job?.error && (
                <p role="alert" className="text-sm text-amber-700 dark:text-amber-300 mt-3">{job.error}</p>
              )}
            </div>
          </div>
          {synthesizing && (
            <progress
              className="w-full mt-4"
              value={job?.progress.processed || 0}
              max={job?.progress.total || 1}
              aria-label="Messages analyzed"
            />
          )}
          {!synthesizing &&
            (!job?.ai_enabled ||
              job.status === "failed" ||
              job.status === "not_started") && (
              <>
                <p className="prose-note mt-3">
                  {job?.ai_enabled
                    ? "Gemini access is already enabled for this conversation. Resume from the last saved passage; completed passages will not be repeated."
                    : "Enable Gemini to send this conversation’s original messages and names to Google for analysis and questions. Usage costs apply. Consent is saved for this conversation."}
                </p>
                <Button className="mt-4" onClick={() => void enqueue()}>
                  {job?.status === "failed"
                    ? "Resume saved analysis"
                    : "Enable Gemini & analyze"}
                </Button>
              </>
            )}
          <Button
            variant="outline"
            className="mt-4 ml-2"
            onClick={() => setAsking({})}
          >
            💬 Ask about this chat
          </Button>
          {job?.status === "completed" && job.ai_enabled && (
            <details className="mt-4">
              <summary className="text-xs cursor-pointer text-secondary">
                Rebuild analysis
              </summary>
              <p className="prose-note my-3">
                Starts a fresh reading of the full history and incurs new API
                usage.
              </p>
              <Button variant="outline" onClick={() => void enqueue(true)}>
                Rebuild with current AI settings
              </Button>
            </details>
          )}
          {aiError && (
            <p role="alert" className="text-red-600 mt-3">
              {aiError}
            </p>
          )}
        </section>
        <header className="scrapbook-cover">
          <div className="cover-copy">
            <span className="scrapbook-label">
              {report.cover?.emoji || "💬"} Your conversation, rediscovered
            </span>
            <h2>{report.cover?.title || report.title}</h2>
            <p className="cover-names">
              {people
                .slice(0, 4)
                .map((p) => p.display_name)
                .join(" + ")}
              {people.length > 4 ? " + the gang" : ""}
            </p>
            <p>
              {report.cover?.subtitle ||
                "The moments, patterns and turning points that make this conversation its own story."}
            </p>
            <div className="cover-pills">
              <span>💬 {number(report.snapshot.messages)} messages</span>
              <span>🌱 {report.snapshot.active_days} days with a hello</span>
              <span>✨ {selected.length} standout discoveries</span>
            </div>
            <button className="wrap-launch" onClick={() => setExporting(true)}>
              🎬 Make a Chat Wrap <span>Video or PDF ↗</span>
            </button>
          </div>
          <div className="cover-art">
            <div className="semantic-emblem" aria-hidden="true">
              {report.cover?.emoji || (group ? "🗨️" : "💬")}
            </div>
            <span className="cover-note">there’s a story in here ✨</span>
          </div>
          <label className="cover-tone">
            Reading mood
            <select
              aria-label="Analysis tone"
              disabled={synthesizing}
              value={tone}
              onChange={(e) => {
                const next = e.target.value as Tone;
                setTone(next);
                localStorage.setItem("chatlens-tone", next);
              }}
            >
              <option value="fun">🪩 Fun</option>
              <option value="balanced">🌿 Balanced</option>
              <option value="analytical">🔎 Analytical</option>
            </select>
          </label>
        </header>
        {report.verdict && (
          <section
            className="rounded-3xl border border-accent/30 bg-accent/10 p-6 sm:p-8"
            aria-label="Final relationship perspective"
          >
            <p className="eyebrow">🫶 The bigger picture · final perspective</p>
            <p className="text-lg leading-relaxed mt-4">
              {report.verdict.summary}
            </p>
            {report.verdict.suggestion && (
              <p className="text-sm mt-4 text-secondary">
                🌱 {report.verdict.suggestion}
              </p>
            )}
            <div className="flex flex-wrap gap-3 mt-4">
              {report.verdict.finding_ids.map((fid) => {
                const finding = allFindings.find((f) => f.id === fid);
                return (
                  finding && (
                    <button
                      key={fid}
                      className="text-xs text-accent"
                      onClick={() => setEvidence(finding)}
                    >
                      {finding.title} ↗
                    </button>
                  )
                );
              })}
              <button
                className="text-xs text-accent"
                onClick={() => setAsking({})}
              >
                💬 Talk this through
              </button>
            </div>
            <p className="text-xs text-secondary mt-4">
              Gemini’s interpretation of the full findings · a perspective, not
              a diagnosis
            </p>
          </section>
        )}
        <nav aria-label="Your scrapbook" className="scrapbook-tabs">
          <a href="#moments">✨ The good bits</a>
          <a href="#micro">🤭 Tiny discoveries</a>
          <a href="#styles">🫶 Your people</a>
          {report.behaviors && (
            <>
              <a href="#who-does-what">👀 Who does what?</a>
              <a href="#personalities">🪞 Personalities</a>
            </>
          )}
          <a href="#eras">📆 Your chapters</a>
        </nav>
        {report.behaviors && (
          <WhoDoesWhat
            data={report.behaviors}
            people={people}
            onEvidence={setEvidence}
          />
        )}
        <section id="moments">
          <SectionIntro
            eyebrow="Worth keeping"
            title="Not just messages. Little moments."
            subtitle="Standout exchanges, shared plans, unexpected turns. Follow the original words behind each reading."
          />
          {ai.length ? (
            <>
              <div
                className="flex flex-wrap gap-2 mb-5"
                aria-label="Moment filters"
              >
                {momentCategories
                  .filter(
                    (c) =>
                      c.id === "all" || ai.some((i) => i.moment_kind === c.id),
                  )
                  .map((c) => (
                    <Button
                      key={c.id}
                      variant={momentFilter === c.id ? "default" : "outline"}
                      aria-pressed={momentFilter === c.id}
                      onClick={() => setMomentFilter(c.id)}
                    >
                      {c.label} ·{" "}
                      {c.id === "all"
                        ? ai.length
                        : ai.filter((i) => i.moment_kind === c.id).length}
                    </Button>
                  ))}
              </div>
              {momentFilter === "tension" && (
                <p className="prose-note mb-5">
                  Disagreements, concerning exchanges, contradictions, and
                  attempts to make things right—when supported by context. These
                  readings do not establish a person’s motives or prove
                  deliberate lying.
                </p>
              )}
              {!visibleMoments.length && (
                <p className="card text-secondary">
                  No supported findings in this category yet. That is not proof
                  that nothing happened; coverage and context may be incomplete.
                </p>
              )}
              <div className="grid md:grid-cols-2 gap-5">
                {render(visibleMoments.slice(0, 6))}
              </div>
              {visibleMoments.length > 6 && (
                <details className="mt-6">
                  <summary className="cursor-pointer text-accent">
                    Explore {visibleMoments.length - 6} more highlights →
                  </summary>
                  <div className="grid md:grid-cols-2 gap-5 mt-5">
                    {render(visibleMoments.slice(6))}
                  </div>
                </details>
              )}
            </>
          ) : (
            <div className="moments-empty">
              <div className="moment-promises">
                <span>🎞️ moments with context</span>
                <span>🔎 patterns worth a second look</span>
                <span>📆 chapters through time</span>
              </div>
              <p>
                {job?.status === "completed"
                  ? "No moments cleared the highlight threshold. Your measured patterns are still available below."
                  : "We’re looking for the moments worth keeping. Analysis progress appears at the top of this report."}
              </p>
              <small>
                We’ll only keep what the messages actually support. No made-up
                romance or happily-ever-afters.
              </small>
            </div>
          )}
        </section>
        <SectionIntro
          eyebrow="Your own kind of rhythm"
          title="Even your habits have personality."
          subtitle="A few little patterns hiding between all those messages. Counted from your chat, not guessed."
        />
        {top.length > 0 ? (
          <section aria-label="Top insights">
            <div className="grid lg:grid-cols-[1.3fr_1fr] gap-4">
              <FindingCard
                finding={top[0]}
                onEvidence={setEvidence}
                title={report.title}
                hero
              />
              <div className="grid gap-4">{render(top.slice(1, 3), true)}</div>
            </div>
            {top.length > 3 && (
              <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4 mt-4">
                {render(top.slice(3))}
              </div>
            )}
          </section>
        ) : (
          <section className="discovery-card">
            <h3 className="text-xl font-semibold">
              A little more history will tell a bigger story.
            </h3>
            <p className="text-sm text-secondary mt-3">
              We found {report.insights.length} grounded observations below.
              This export doesn’t yet show enough contrast for a headline
              finding.
            </p>
          </section>
        )}
        <nav aria-label="Report sections" className="report-jump">
          <a href="#micro">
            Little discoveries
            <ArrowDown size={12} />
          </a>
          <a href="#styles">The cast</a>
          <a href="#eras">The eras</a>
          {group && <a href="#pairs">The duos</a>}
          <a href="#topics">Words & themes</a>
          <a href="#methodology">How it works</a>
        </nav>
        {micro.length > 0 && (
          <section id="micro">
            <SectionIntro
              eyebrow="🤭 Blink and you’d miss it"
              title="Things you probably never noticed"
              subtitle="The tiny records and recurring rhythms that make this conversation yours."
            />
            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {render(micro, true)}
            </div>
          </section>
        )}
        {cards.length > 0 && (
          <section id="styles">
            <SectionIntro
              eyebrow="🫶 The people in these pages"
              title={
                group
                  ? "Everyone brings their own thing."
                  : "Two people. Different chat habits."
              }
              subtitle="The little ways you each show up in the conversation."
            />
            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {cards.map((i) => (
                <FindingCard
                  key={i.id}
                  finding={i}
                  onEvidence={setEvidence}
                  title={report.title}
                  person={
                    people.find((p) => p.id === i.participant_ids[0])
                      ?.display_name
                  }
                />
              ))}
            </div>
          </section>
        )}
        <section id="eras">
          <SectionIntro
            eyebrow="📆 Remember this chapter?"
            title={
              report.timeline.length > 1
                ? "Your chat, era by era."
                : "The story so far."
            }
            subtitle="The busy stretches, the quiet pauses, and the times your chat found a new rhythm."
          />
          {report.timeline.length > 0 ? (
            <>
              <StoryTimeline
                cover={report.cover}
                moments={report.synthesis?.insights || []}
                onEvidence={setEvidence}
              />
              <details className="mt-5">
                <summary className="text-sm cursor-pointer">
                  Month-by-month measurements
                </summary>
                <Timeline periods={report.timeline} onEvidence={setEvidence} />
              </details>
            </>
          ) : (
            <p className="card text-secondary">
              No participant messages are available for a timeline.
            </p>
          )}
        </section>
        {group && (
          <section id="pairs">
            <ReplyNetwork id={id} onEvidence={setEvidence} />
            <SectionIntro
              eyebrow="The duos"
              title="Some exchanges have a rhythm."
              subtitle="Only explicit replies and known reactions count as pair interactions."
            />
            {pair.length ? (
              <div className="grid md:grid-cols-2 gap-4">{render(pair)}</div>
            ) : (
              <div className="card text-sm text-secondary leading-relaxed">
                This export doesn’t contain enough reliable reply or reaction
                links to single out a duo. The activity and participant findings
                above still use every recorded message.
              </div>
            )}
          </section>
        )}
        {group && awards.length > 0 && (
          <section>
            <SectionIntro
              eyebrow="🏆 Completely unofficial, entirely yours"
              title="And the group-chat award goes to…"
              subtitle="A clear lead, a real measurement, a little recognition. Ties don’t get an invented winner."
            />
            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {render(awards, true)}
            </div>
          </section>
        )}
        {topics.length > 0 && (
          <section id="topics">
            <SectionIntro
              eyebrow="🦜 You do have a way with words"
              title="Words that keep coming back."
              subtitle="Literal language patterns are measured locally. Gemini interpretations, when requested, are labelled separately."
            />
            <div className="grid md:grid-cols-2 gap-4">{render(topics)}</div>
          </section>
        )}
        {deep.length > 0 && (
          <section>
            <SectionIntro
              eyebrow="🍿 There’s a little more"
              title="A few more things that are so you."
              subtitle="More timing habits, communication contrasts, and changes worth a closer look."
            />
            <div className="grid md:grid-cols-2 gap-4">{render(deep)}</div>
          </section>
        )}
        <section id="methodology" className="border-t border-border pt-7">
          <details open={tone === "analytical"}>
            <summary className="cursor-pointer text-sm font-medium flex items-center gap-2">
              <ShieldCheck size={16} />
              Behind the discoveries: evidence & methodology
            </summary>
            <div className="mt-5 grid md:grid-cols-2 gap-x-8 gap-y-4">
              {report.methodology.map((m, i) => (
                <p key={i} className="prose-note">
                  {m}
                </p>
              ))}
            </div>
            <p className="prose-note mt-5">
              Clock: {report.timezone} · Session gap: {report.session_gap_hours}
              h · {report.coverage.explicit_replies} explicit replies ·{" "}
              {report.coverage.known_reactions} identifiable reactions.{" "}
              {report.coverage.small_sample
                ? "This is a small export; treat patterns as a snapshot, not a settled habit."
                : ""}
            </p>
          </details>
          <p className="prose-note mt-5">
            No telemetry. Gemini runs on the server for conversations you
            enabled at upload or here. Save-card downloads include finding text
            and names. Evidence drawer messages are not added.
          </p>
        </section>
        {asking && (
          <AskChat
            id={id}
            finding={asking.finding}
            onClose={() => setAsking(null)}
            onEvidence={setEvidence}
          />
        )}
        {evidence && (
          <Evidence
            id={id}
            finding={evidence}
            onClose={() => setEvidence(null)}
          />
        )}
      </div>
    </ChatContext.Provider>
  );
}
function SectionIntro({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mb-6">
      <p className="eyebrow text-accent">{eyebrow}</p>
      <h2 className="text-2xl sm:text-3xl tracking-tight mt-2">{title}</h2>
      <p className="text-sm text-secondary leading-relaxed mt-3 max-w-2xl">
        {subtitle}
      </p>
    </div>
  );
}
