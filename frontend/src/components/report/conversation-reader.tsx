"use client";
import { useEffect, useRef, useState } from "react";
import { api, date } from "@/lib/api";
import type { Finding } from "@/lib/report-types";
import type { Message } from "@/lib/types";
import { useChatContext } from "./chat-context";
type Page = { items: Message[]; has_before: boolean; has_after: boolean };
export function Evidence({
  id,
  finding,
  onClose,
}: {
  id: string;
  finding: Finding;
  onClose: () => void;
}) {
  const { me } = useChatContext();
  const dialog = useRef<HTMLDialogElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const busy = useRef(false);
  const [page, setPage] = useState<Page>({
    items: [],
    has_before: false,
    has_after: false,
  });
  const [anchor, setAnchor] = useState(finding.evidence_ids[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const request = useRef<AbortController | null>(null);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => {
      request.current?.abort();
      element?.close();
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    request.current?.abort();
    request.current = controller;
    busy.current = true;
    setLoading(true);
    setError("");
    api<Page>(`/conversations/${id}/messages/${anchor}/context`, {
      signal: controller.signal,
    })
      .then((data) => {
        setPage(data);
        requestAnimationFrame(() => {
          const target = viewport.current?.querySelector(
            `[data-message-id="${anchor}"]`,
          ) as HTMLElement | null;
          if (target && viewport.current)
            viewport.current.scrollTop = target.offsetTop - 80;
        });
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          busy.current = false;
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [id, anchor]);
  async function more(direction: "before" | "after") {
    if (busy.current || !page.items.length) return;
    busy.current = true;
    setLoading(true);
    setError("");
    const controller = new AbortController();
    request.current = controller;
    const edge =
      direction === "before"
        ? page.items[0]
        : page.items[page.items.length - 1];
    const boundary = viewport.current?.getBoundingClientRect().top || 0;
    const visible = Array.from(
      viewport.current?.querySelectorAll<HTMLElement>("[data-message-id]") ||
        [],
    ).find((el) => el.getBoundingClientRect().bottom > boundary);
    const visibleId = visible?.dataset.messageId;
    const visibleTop = visible?.getBoundingClientRect().top || 0;
    try {
      const data = await api<Page>(
        `/conversations/${id}/messages/${edge.id}/context?direction=${direction}`,
        { signal: controller.signal },
      );
      setPage((old) => {
        const incoming = data.items.filter(
          (m) => !old.items.some((o) => o.id === m.id),
        );
        const combined =
          direction === "before"
            ? [...incoming, ...old.items]
            : [...old.items, ...incoming];
        return {
          items:
            direction === "before"
              ? combined.slice(0, 300)
              : combined.slice(-300),
          has_before:
            direction === "before"
              ? data.has_before
              : old.has_before || combined.length > 300,
          has_after:
            direction === "after"
              ? data.has_after
              : old.has_after || combined.length > 300,
        };
      });
      requestAnimationFrame(() => {
        const kept = viewport.current?.querySelector<HTMLElement>(
          `[data-message-id="${visibleId}"]`,
        );
        if (viewport.current && kept)
          viewport.current.scrollTop +=
            kept.getBoundingClientRect().top - visibleTop;
      });
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    } finally {
      if (!controller.signal.aborted) {
        busy.current = false;
        setLoading(false);
      }
    }
  }
  return (
    <dialog
      ref={dialog}
      onCancel={onClose}
      aria-label={`Evidence: ${finding.title}`}
      className="evidence-dialog bg-surface text-foreground border border-border rounded-2xl p-0"
    >
      <header className="p-5 border-b border-border">
        <div className="flex justify-between gap-4">
          <div>
            <p className="eyebrow">Back in the conversation</p>
            <h2 className="text-xl mt-2">{finding.title}</h2>
          </div>
          <button onClick={onClose} aria-label="Close evidence">
            ✕
          </button>
        </div>
        <p className="text-xs text-secondary mt-3">
          Scroll both ways through the original chat. Highlighted bubbles
          support this finding.
        </p>
        <div
          className="flex gap-2 overflow-x-auto mt-3"
          aria-label="Jump to source message"
        >
          {finding.evidence_ids.map((mid, i) => (
            <button
              key={mid}
              disabled={loading}
              aria-pressed={anchor === mid}
              onClick={() => setAnchor(mid)}
              className="shrink-0 rounded-full border border-border px-3 py-1 text-xs"
            >
              Source {i + 1} ↗
            </button>
          ))}
        </div>
        <details className="text-xs text-secondary mt-3">
          <summary>About this finding</summary>
          <p>{finding.method}</p>
          <p>{finding.caveat}</p>
        </details>
      </header>
      {error && (
        <p role="alert" className="p-3 text-red-600 text-sm">
          {error}
        </p>
      )}
      <div
        ref={viewport}
        className="relative overflow-y-auto p-4 sm:p-6 space-y-4"
        style={{ height: "min(65vh, 720px)", overflowAnchor: "none" }}
        aria-label="Scrollable original conversation"
        onScroll={() => {
          const el = viewport.current;
          if (!el || busy.current || error) return;
          if (el.scrollTop < 120 && page.has_before) void more("before");
          else if (
            el.scrollHeight - el.scrollTop - el.clientHeight < 120 &&
            page.has_after
          )
            void more("after");
        }}
      >
        {page.has_before ? (
          <button
            disabled={loading}
            className="block mx-auto text-xs text-accent"
            onClick={() => void more("before")}
          >
            ↑ Earlier messages
          </button>
        ) : (
          !loading && (
            <p className="text-center text-xs text-secondary">
              Beginning of conversation
            </p>
          )
        )}
        {page.items.map((m) => (
          <article
            key={m.id}
            data-message-id={m.id}
            className={`chat-bubble ${m.sender_id === me ? "chat-mine" : ""} ${finding.evidence_ids.includes(m.id) ? "ring-2 ring-accent" : ""}`}
          >
            <div className="flex flex-wrap justify-between gap-2">
              <span className="text-xs font-semibold">
                {m.sender_name || "System"}
              </span>
              <time className="text-[10px] text-secondary">
                {date(m.timestamp, true)} · UTC
              </time>
            </div>
            <p className="text-sm whitespace-pre-wrap break-words leading-relaxed mt-2">
              {m.text || `[${m.message_type}]`}
            </p>
          </article>
        ))}
        {loading && (
          <p role="status" className="text-center text-xs">
            Loading messages…
          </p>
        )}
        {page.has_after ? (
          <button
            disabled={loading}
            className="block mx-auto text-xs text-accent"
            onClick={() => void more("after")}
          >
            Later messages ↓
          </button>
        ) : (
          !loading && (
            <p className="text-center text-xs text-secondary">
              End of conversation
            </p>
          )
        )}
      </div>
    </dialog>
  );
}
