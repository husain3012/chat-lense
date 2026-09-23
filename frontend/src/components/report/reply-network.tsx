"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Finding } from "@/lib/report-types";
type Edge = {
  source: string;
  target: string;
  weight: number;
  forward: number;
  backward: number;
  evidence_ids: string[];
};
type Network = {
  nodes: { id: string; name: string; replies_sent: number }[];
  edges: Edge[];
  total_replies: number;
  method: string;
};
export function ReplyNetwork({
  id,
  onEvidence,
}: {
  id: string;
  onEvidence: (f: Finding) => void;
}) {
  const [network, setNetwork] = useState<Network | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    api<{ network: Network | null }>(`/conversations/${id}/reply-network`, {
      signal: controller.signal,
    })
      .then((d) => setNetwork(d.network))
      .catch((e) => {
        if (e.name !== "AbortError")
          setError("Reply network could not load. Refresh to retry.");
      });
    return () => controller.abort();
  }, [id]);
  if (error)
    return (
      <p className="prose-note" role="status">
        {error}
      </p>
    );
  if (!network) return null;
  const method = network.method;
  const names = new Map(network.nodes.map((n) => [n.id, n.name]));
  const degree = new Map<string, number>();
  for (const edge of network.edges) {
    degree.set(edge.source, (degree.get(edge.source) || 0) + edge.weight);
    degree.set(edge.target, (degree.get(edge.target) || 0) + edge.weight);
  }
  const strength = (pid: string) => degree.get(pid) || 0;
  const nodes = network.nodes
    .filter((n) => strength(n.id) > 0)
    .sort((a, b) => strength(b.id) - strength(a.id))
    .slice(0, 20);
  const position = new Map(
    nodes.map((n, i) => [
      n.id,
      {
        x: 320 + Math.cos((i / nodes.length) * Math.PI * 2 - Math.PI / 2) * 235,
        y: 270 + Math.sin((i / nodes.length) * Math.PI * 2 - Math.PI / 2) * 205,
      },
    ]),
  );
  const max = Math.max(...network.edges.map((e) => e.weight));
  const edges = network.edges.filter(
    (e) => !selected || e.source === selected || e.target === selected,
  );
  function evidence(edge: Edge) {
    onEvidence({
      id: `reply-${edge.source}-${edge.target}`,
      family: "reply-network",
      category: "Explicit replies",
      section: "pairs",
      title: `${names.get(edge.source)} ↔ ${names.get(edge.target)}`,
      description: method,
      value: String(edge.weight),
      label: "Explicit replies",
      participant_ids: [edge.source, edge.target],
      facts: [
        { label: "Replies exchanged", value: edge.weight, unit: "replies" },
      ],
      evidence_ids: edge.evidence_ids,
      evidence_total: edge.weight,
      method,
      caveat: "More replies do not establish a closer relationship.",
      visual_type: "none",
      visual: [],
      interpretation: false,
      source: "measured",
    });
  }
  return (
    <section
      className="rounded-3xl border border-border bg-surface p-5 sm:p-8"
      aria-label="Group reply network"
    >
      <p className="eyebrow">🕸️ Who talks with whom</p>
      <h3 className="text-2xl mt-2">The group’s reply connections</h3>
      <p className="prose-note mt-3">
        {network.total_replies.toLocaleString()} explicit replies. Thicker lines
        mean more replies exchanged; they don’t measure emotional closeness.
      </p>
      <label className="block text-sm mt-4">
        Explore a participant
        <select
          className="block w-full mt-2"
          value={selected || ""}
          onChange={(e) => setSelected(e.target.value || null)}
        >
          <option value="">Everyone</option>
          {network.nodes.map((n) => (
            <option key={n.id} value={n.id}>
              {n.name}
            </option>
          ))}
        </select>
      </label>
      <svg
        viewBox="0 0 640 540"
        className="w-full max-w-2xl mx-auto"
        role="img"
        aria-label="Weighted explicit-reply network; exact counts and evidence follow below"
      >
        {edges.map((e) => {
          const a = position.get(e.source),
            b = position.get(e.target);
          return (
            a &&
            b && (
              <line
                key={`${e.source}-${e.target}`}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke="var(--accent, #8b5cf6)"
                strokeWidth={1 + 9 * Math.sqrt(e.weight / max)}
                opacity={0.45}
              >
                <title>
                  {names.get(e.source)} ↔ {names.get(e.target)}: {e.weight}{" "}
                  replies
                </title>
              </line>
            )
          );
        })}
        {nodes.map((n) => {
          const p = position.get(n.id)!;
          return (
            <g key={n.id}>
              <circle cx={p.x} cy={p.y} r={18} fill="var(--accent, #8b5cf6)" />
              <text
                x={p.x}
                y={p.y + 4}
                textAnchor="middle"
                fontSize="12"
                fill="white"
              >
                {n.name.slice(0, 1)}
              </text>
              <text
                x={p.x}
                y={p.y + 36}
                textAnchor="middle"
                fontSize="12"
                fill="currentColor"
              >
                {n.name.length > 18 ? n.name.slice(0, 16) + "…" : n.name}
              </text>
            </g>
          );
        })}
      </svg>
      {network.nodes.length > 20 && (
        <p className="prose-note">
          Graph shows the 20 participants with the most reply traffic. Use the
          selector to inspect anyone’s pairs below.
        </p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left">
              <th className="p-2">Pair</th>
              <th>Replies</th>
              <th>Each direction</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {edges.slice(0, 10).map((e) => (
              <tr
                key={`${e.source}-${e.target}`}
                className="border-t border-border"
              >
                <td className="p-2">
                  {names.get(e.source)} ↔ {names.get(e.target)}
                </td>
                <td>{e.weight}</td>
                <td>
                  {e.forward} → · {e.backward} ←
                </td>
                <td>
                  <button className="text-accent" onClick={() => evidence(e)}>
                    Read exchanges ↗
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="prose-note mt-3">
        Top {Math.min(10, edges.length)} observed pairs
        {selected ? " for this participant" : ""}. Missing reply links cannot be
        inferred from message order.
      </p>
    </section>
  );
}
