"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Calendar, Trash2 } from "lucide-react";
import { ReportView } from "@/components/report/report";
import { Overview, Metric } from "@/components/overview";
import { Messages } from "@/components/messages";
import { Button } from "@/components/ui/button";
import { TimeChart, ActivityBar } from "@/components/charts";
import { api, date, duration, number } from "@/lib/api";
import type { Conversation, Person, Analytics, StatsPerson } from "@/lib/types";
export default function ConversationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const [c, setC] = useState<Conversation | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [a, setA] = useState<Analytics | null>(null);
  const [tab, setTab] = useState("Report");
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [selected, setSelected] = useState<StatsPerson | null>(null);
  useEffect(() => {
    Promise.all([
      api<Conversation>("/conversations/" + id),
      api<Person[]>(`/conversations/${id}/participants`),
    ])
      .then(([chat, p]) => {
        setC(chat);
        setPeople(p);
      })
      .catch((e) => setError(e.message));
  }, [id]);
  useEffect(() => {
    if (a || (tab !== "Statistics" && tab !== "Participants")) return;
    const controller = new AbortController();
    const gap = localStorage.getItem("chatlens-gap") || "4";
    api<Analytics>(
      `/conversations/${id}/analytics?session_gap=${encodeURIComponent(gap)}`,
      { signal: controller.signal },
    )
      .then(setA)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [id, tab, a]);
  async function remove() {
    setDeleting(true);
    try {
      await api(`/conversations/${id}`, { method: "DELETE" });
      router.push("/");
    } catch (e) {
      setError((e as Error).message);
      setDeleting(false);
    }
  }
  if (!c)
    return (
      <div className="card" role="status">
        {error || "Loading conversation and calculating statistics…"}
      </div>
    );
  return (
    <>
      <Link
        href="/"
        className="text-xs text-secondary flex items-center gap-2 mb-6"
      >
        <ArrowLeft size={14} />
        All conversations
      </Link>
      <div className="flex justify-between items-start gap-4">
        <div>
          <div className="flex gap-2 items-center mb-3">
            <span className="badge">{c.platform}</span>
            <span className="badge">{c.conversation_type}</span>
          </div>
          <h1>{c.title}</h1>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-secondary mt-3">
            <span className="flex items-center gap-1.5">
              <Calendar size={13} />
              {date(c.started_at)} — {date(c.ended_at)}
            </span>
            <span>{number(c.message_count)} messages</span>
            <span>{people.length} participants</span>
          </div>
        </div>
        <Button
          variant="ghost"
          aria-label="Delete conversation"
          onClick={() => setConfirm(true)}
        >
          <Trash2 size={16} />
          <span className="hidden sm:inline">Delete chat</span>
        </Button>
      </div>
      {confirm && (
        <div
          role="alertdialog"
          aria-label="Delete conversation confirmation"
          className="card border-red-300 mt-5"
        >
          <h2>Delete this conversation?</h2>
          <p className="text-sm text-secondary mt-2 mb-4">
            All imported messages and participants will be permanently removed.
          </p>
          <div className="flex gap-2">
            <Button
              variant="destructive"
              disabled={deleting}
              onClick={() => void remove()}
            >
              {deleting ? "Deleting…" : "Delete conversation"}
            </Button>
            <Button
              variant="outline"
              disabled={deleting}
              onClick={() => setConfirm(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
      {error && (
        <p role="alert" className="text-red-600 mt-4">
          {error}
        </p>
      )}
      <div
        role="tablist"
        aria-label="Conversation sections"
        className="flex gap-5 overflow-x-auto border-b border-border mt-8 mb-7"
      >
        {["Report", "Statistics", "Messages", "Participants"].map((t) => (
          <button
            role="tab"
            aria-selected={tab === t}
            key={t}
            onClick={() => setTab(t)}
            className={`pb-3 text-sm border-b-2 ${tab === t ? "border-accent text-accent font-medium" : "border-transparent text-secondary"}`}
          >
            {t}
          </button>
        ))}
      </div>
      <div hidden={tab !== "Report"}>
        <ReportView
          id={id}
          people={people}
          group={c.conversation_type === "group"}
          sourceTimezone={c.metadata?.source_timezone}
        />
      </div>
      {(tab === "Statistics" || tab === "Participants") && !a && (
        <p role="status" className="card">
          Loading statistics…
        </p>
      )}
      {tab === "Statistics" && a && (
        <Overview
          a={a}
          group={c.conversation_type === "group"}
          peopleCount={people.length}
        />
      )}
      {tab === "Messages" && <Messages id={id} people={people} />}
      {tab === "Participants" && a && (
        <>
          <div className="flex justify-between mb-4">
            <h2>Participant activity</h2>
            <span className="prose-note">Select a participant to explore</span>
          </div>
          <div className="card p-0 overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  {[
                    "Participant",
                    "Messages",
                    "Share",
                    "Avg. length",
                    "Active days",
                    "Sessions started",
                    "Median response",
                  ].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {a.participants.map((p) => (
                  <tr key={p.id} className="hover:bg-muted">
                    <td>
                      <button
                        className="text-accent text-left"
                        onClick={() => setSelected(p)}
                      >
                        {p.name}
                        {p.is_current_user && (
                          <span className="badge ml-2">You</span>
                        )}
                      </button>
                    </td>
                    <td>{number(p.message_count)}</td>
                    <td>{p.percentage.toFixed(1)}%</td>
                    <td>{Math.round(p.average_length)} chars</td>
                    <td>{p.active_days}</td>
                    <td>{p.sessions_started}</td>
                    <td>{duration(p.response_times?.median)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="prose-note mt-3">
            {a.response_method}. Length measures text messages only; shares
            include system messages in the total.
          </p>
          {selected && (
            <div className="mt-6 space-y-5">
              <div className="flex justify-between">
                <h2 className="text-lg">{selected.name}</h2>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelected(null)}
                >
                  Close details
                </Button>
              </div>
              <div className="grid sm:grid-cols-3 gap-4">
                <Metric
                  label="Text messages"
                  value={number(selected.text_count)}
                />
                <Metric
                  label="Media messages"
                  value={number(selected.media_count)}
                />
                <Metric
                  label="Characters"
                  value={number(selected.total_characters)}
                />
              </div>
              <div className="grid xl:grid-cols-2 gap-4">
                <section className="card min-w-0">
                  <h2>Activity over time</h2>
                  <TimeChart data={selected.activity.daily} />
                </section>
                <section className="card min-w-0">
                  <h2>Common active hours</h2>
                  <ActivityBar data={selected.activity.hourly} />
                </section>
              </div>
              <section className="card">
                <h2>Message distribution</h2>
                <div className="flex flex-wrap gap-6 mt-4">
                  {Object.entries(selected.types).map(([type, count]) => (
                    <p key={type} className="text-sm capitalize">
                      {type} <strong className="ml-2">{number(count)}</strong>
                    </p>
                  ))}
                </div>
                {selected.response_times && (
                  <p className="prose-note mt-5">
                    Response times · Mean{" "}
                    {duration(selected.response_times.mean)} · P25{" "}
                    {duration(selected.response_times.p25)} · P75{" "}
                    {duration(selected.response_times.p75)} · P90{" "}
                    {duration(selected.response_times.p90)} ·{" "}
                    {selected.response_times.count} observations
                  </p>
                )}
              </section>
              <Button
                variant="outline"
                onClick={async () => {
                  try {
                    await api(
                      `/conversations/${id}/participants/${selected.id}`,
                      {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ is_current_user: true }),
                      },
                    );
                    setA({
                      ...a,
                      participants: a.participants.map((p) => ({
                        ...p,
                        is_current_user: p.id === selected.id,
                      })),
                    });
                    setSelected({ ...selected, is_current_user: true });
                    setPeople(
                      people.map((p) => ({
                        ...p,
                        is_current_user: p.id === selected.id,
                      })),
                    );
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                Set as current user
              </Button>
            </div>
          )}
        </>
      )}
    </>
  );
}
