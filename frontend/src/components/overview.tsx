"use client";
import { useState } from "react";
import { MessageSquare, Users, Calendar, Activity, Clock } from "lucide-react";
import { TimeChart, ActivityBar, ShareChart } from "@/components/charts";
import { number, duration } from "@/lib/api";
import type { Analytics } from "@/lib/types";
export function Metric({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon?: typeof MessageSquare;
}) {
  return (
    <div className="card p-5">
      <div className="flex justify-between text-secondary mb-4">
        <span className="text-xs">{label}</span>
        {Icon && <Icon size={15} />}
      </div>
      <p className="text-2xl lg:text-3xl font-semibold tracking-tight">
        {value}
      </p>
    </div>
  );
}
export function Overview({
  a,
  group,
  peopleCount,
}: {
  a: Analytics;
  group: boolean;
  peopleCount: number;
}) {
  const [period, setPeriod] = useState<"daily" | "weekly" | "monthly">("daily");
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <Metric
          label="Messages"
          value={number(a.total_messages)}
          icon={MessageSquare}
        />
        <Metric label="Participants" value={number(peopleCount)} icon={Users} />
        <Metric
          label="Active days"
          value={number(a.active_days)}
          icon={Calendar}
        />
        <Metric
          label="Messages / active day"
          value={number(a.messages_per_active_day)}
          icon={Activity}
        />
        <Metric
          label="Sessions"
          value={number(a.sessions.total)}
          icon={Clock}
        />
      </div>
      <div className="grid xl:grid-cols-[1.45fr_1fr] gap-5">
        <section className="card min-w-0">
          <div className="flex justify-between items-center">
            <div>
              <h2>Messages over time</h2>
              <p className="prose-note mt-1">The rhythm of your conversation</p>
            </div>
            <select
              aria-label="Chart time interval"
              className="text-xs min-h-8 py-1"
              value={period}
              onChange={(e) => setPeriod(e.target.value as typeof period)}
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
          <TimeChart data={a.activity[period]} />
        </section>
        <section className="card min-w-0">
          <h2>Who’s talking</h2>
          <p className="prose-note mt-1">Share of all messages</p>
          <ShareChart people={a.participants} />
        </section>
      </div>
      <div className="grid lg:grid-cols-2 gap-5">
        <section className="card min-w-0">
          <h2>Activity by hour</h2>
          <p className="prose-note mt-1">
            When the conversation comes to life · UTC
          </p>
          <ActivityBar data={a.activity.hourly} />
        </section>
        <section className="card min-w-0">
          <h2>Activity by weekday</h2>
          <p className="prose-note mt-1">Your week, in messages</p>
          <ActivityBar data={a.activity.weekday} />
        </section>
      </div>
      <section className="card">
        <h2>Conversation rhythm</h2>
        <p className="prose-note mt-1">
          A new session begins after more than {a.sessions.gap_hours} hours
          without a message.
        </p>
        <div className="grid sm:grid-cols-4 gap-5 mt-5">
          {[
            ["Messages / session", a.sessions.average_messages.toFixed(1)],
            ["Median session", duration(a.sessions.median_length_seconds)],
            ["Longest session", duration(a.sessions.longest_seconds)],
            ["Longest quiet stretch", duration(a.longest_inactivity_seconds)],
          ].map(([k, v]) => (
            <div key={k}>
              <p className="text-xl font-medium">{v}</p>
              <p className="prose-note mt-1">{k}</p>
            </div>
          ))}
        </div>
      </section>
      {group && (
        <div className="grid lg:grid-cols-2 gap-5">
          <section className="card">
            <h2>Participant activity</h2>
            <div className="space-y-5 mt-6">
              {a.participants
                .slice()
                .sort((x, y) => y.message_count - x.message_count)
                .map((p) => (
                  <div key={p.id}>
                    <div className="flex justify-between text-xs mb-2">
                      <span>{p.name}</span>
                      <span className="text-secondary">
                        {number(p.message_count)} · {p.percentage.toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-muted rounded-full">
                      <div
                        className="bg-accent h-1.5 rounded-full"
                        style={{ width: `${p.percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          </section>
          <section className="card overflow-x-auto">
            <h2>Measured interactions</h2>
            <p className="prose-note mt-1 mb-4">
              Rows → columns · explicit replies, mentions, and identifiable
              reactions.
            </p>
            {a.interactions ? (
              <table className="w-full">
                <thead>
                  <tr>
                    <th>From / To</th>
                    {a.interactions.participants.map((p) => (
                      <th key={p.id}>{p.name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {a.interactions.participants.map((p, i) => (
                    <tr key={p.id}>
                      <td>{p.name}</td>
                      {a.interactions!.matrix[i].map((v, j) => (
                        <td
                          key={j}
                          style={{
                            background: v
                              ? `rgba(119,112,221,${Math.min(0.55, 0.08 + v * 0.03)})`
                              : undefined,
                          }}
                        >
                          {v || "—"}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="bg-muted rounded-lg p-6 text-sm text-secondary">
                Unavailable for this export. No reliable interaction signals
                were found.
              </div>
            )}
          </section>
        </div>
      )}
      <section className="card">
        <h2>Reactions</h2>
        {a.reactions ? (
          <>
            <p className="text-sm mt-3">
              {number(a.reactions.total)} reactions ·{" "}
              {Object.entries(a.reactions.common)
                .map(([emoji, n]) => `${emoji} ${n}`)
                .join("  ") || "None recorded"}
            </p>
            <div className="flex flex-wrap gap-5 mt-4">
              {a.participants.map((p) => (
                <p key={p.id} className="prose-note">
                  {p.name}: {a.reactions!.given[p.id] || 0} given ·{" "}
                  {a.reactions!.received[p.id] || 0} received
                </p>
              ))}
            </div>
            <p className="prose-note mt-3">{a.reactions.note}</p>
          </>
        ) : (
          <p className="prose-note mt-3">
            Reaction data is unavailable in this export format.
          </p>
        )}
      </section>
      <p className="prose-note">
        Calculated from imported messages. {a.timezone}. No inferred
        relationships or sentiment.
      </p>
    </div>
  );
}
