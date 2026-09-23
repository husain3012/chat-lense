"use client";
import { useState, useEffect } from "react";
import { Search, Reply, Smile } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, date, number } from "@/lib/api";
import type { Message, Person } from "@/lib/types";
export function Messages({ id, people }: { id: string; people: Person[] }) {
  const [data, setData] = useState<{ items: Message[]; total: number } | null>(
    null,
  );
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [participant, setParticipant] = useState("");
  const [type, setType] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoading(true);
      const params = new URLSearchParams({
        page: String(page),
        page_size: "50",
      });
      if (q) params.set("q", q);
      if (participant) params.set("participant", participant);
      if (type) params.set("message_type", type);
      if (start) params.set("start", start + "T00:00:00Z");
      if (end) params.set("end", end + "T23:59:59.999999Z");
      api<{ items: Message[]; total: number }>(
        `/conversations/${id}/messages?${params}`,
        { signal: controller.signal },
      )
        .then((d) => {
          setData(d);
          setError("");
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [id, page, q, participant, type, start, end]);
  return (
    <>
      <div className="card mb-5 p-4">
        <div className="flex flex-wrap gap-3">
          <label className="relative flex-1 min-w-44">
            <Search
              size={15}
              className="absolute left-3 top-3 text-secondary"
            />
            <input
              aria-label="Search messages"
              className="w-full pl-9 text-sm"
              placeholder="Search messages…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <select
            aria-label="Filter participant"
            className="text-sm"
            value={participant}
            onChange={(e) => {
              setParticipant(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All participants</option>
            {people.map((p) => (
              <option key={p.id} value={p.id}>
                {p.display_name}
              </option>
            ))}
          </select>
          <select
            aria-label="Message type"
            className="text-sm"
            value={type}
            onChange={(e) => {
              setType(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All message types</option>
            {[
              "text",
              "image",
              "video",
              "audio",
              "file",
              "sticker",
              "call",
              "system",
              "other",
            ].map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-secondary">
          <label>
            From{" "}
            <input
              aria-label="Start date"
              type="date"
              value={start}
              onChange={(e) => {
                setStart(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label>
            To{" "}
            <input
              aria-label="End date"
              type="date"
              value={end}
              onChange={(e) => {
                setEnd(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <span className="ml-auto">
            {loading ? "Loading…" : `${number(data?.total || 0)} messages`}
          </span>
        </div>
      </div>
      {error && (
        <p role="alert" className="text-red-600">
          {error}
        </p>
      )}
      <div className="card p-0 overflow-hidden">
        {data?.items.map((m) => (
          <article
            key={m.id}
            className={`chat-bubble ${people.some((p) => p.id === m.sender_id && p.is_current_user) ? "chat-mine" : ""}`}
          >
            <div className="flex flex-wrap gap-2 items-center">
              <span className="font-medium text-sm">
                {m.sender_name || "System"}
              </span>
              <time className="text-[11px] text-secondary">
                {date(m.timestamp, true)}
              </time>
              {m.message_type !== "text" && (
                <span className="badge">{m.message_type}</span>
              )}
            </div>
            {m.reply_to_id && (
              <p className="prose-note flex items-center gap-1 mt-2">
                <Reply size={12} />
                Reply to message {m.reply_to_id}
              </p>
            )}
            <p className="text-sm leading-7 whitespace-pre-wrap break-words mt-2">
              {m.text ||
                (m.metadata.body_unavailable
                  ? "Message body unavailable"
                  : "No text content")}
            </p>
            {m.attachments.length > 0 && (
              <p className="prose-note mt-2">
                {m.attachments.length} media reference(s) · media files are not
                stored
              </p>
            )}
            {m.reactions.length > 0 && (
              <p className="prose-note flex items-center gap-2 mt-2">
                <Smile size={13} />
                {m.reactions.map((r) => `${r.emoji} ${r.count}`).join(" · ")}
              </p>
            )}
          </article>
        ))}
        {data?.items.length === 0 && (
          <p className="p-10 text-secondary text-sm text-center">
            No messages match these filters.
          </p>
        )}
        {!data && !error && (
          <p className="p-10 text-secondary">Loading messages…</p>
        )}
      </div>
      <div className="flex items-center justify-between mt-5">
        <span className="prose-note">
          Page {page} of {Math.max(1, Math.ceil((data?.total || 0) / 50))}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={page === 1 || loading}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            disabled={!data || page * 50 >= data.total || loading}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </>
  );
}
