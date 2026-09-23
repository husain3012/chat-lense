"use client";
import { useEffect, useRef, useState } from "react";
import { X, ChevronDown, Quote } from "lucide-react";
import { api, date } from "@/lib/api";
import type { Finding } from "@/lib/report-types";
import type { Message } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { useChatContext } from "./chat-context";
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
  const [items, setItems] = useState<Message[]>([]);
  const [error, setError] = useState("");
  const [contexts, setContexts] = useState<Record<string, Message[]>>({});
  const [loading, setLoading] = useState(true);
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setItems([]);
    setContexts({});
    api<{ items: Message[] }>(
      `/conversations/${id}/evidence?ids=${encodeURIComponent(finding.evidence_ids.join(","))}`,
      { signal: controller.signal },
    )
      .then((d) => setItems(d.items))
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [id, finding]);
  async function context(mid: string) {
    try {
      const d = await api<{ items: Message[] }>(
        `/conversations/${id}/messages/${mid}/context`,
      );
      setContexts((old) => ({ ...old, [mid]: d.items }));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <dialog
      ref={ref}
      aria-label={`Evidence: ${finding.title}`}
      onCancel={onClose}
      className="evidence-dialog bg-surface text-foreground border border-border rounded-2xl p-0"
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="p-6 sm:p-8">
        <div className="flex justify-between gap-4">
          <div>
            <p className="eyebrow mb-2">Behind the finding</p>
            <h2 className="text-2xl tracking-tight">{finding.title}</h2>
          </div>
          <Button variant="ghost" onClick={onClose} aria-label="Close evidence">
            <X size={18} />
          </Button>
        </div>
        <p className="text-sm text-secondary mt-4 leading-relaxed">
          {finding.method}
        </p>
        {finding.caveat && (
          <p className="text-xs text-secondary mt-3 border-l-2 border-accent pl-3">
            {finding.caveat}
          </p>
        )}
        <div className="grid grid-cols-2 gap-3 mt-5">
          {finding.facts.map((f, i) => (
            <div key={i} className="p-3 rounded-lg bg-muted">
              <p className="text-xs text-secondary">{f.label}</p>
              <p className="text-lg font-medium mt-1">
                {Number.isInteger(f.value)
                  ? f.value.toLocaleString()
                  : f.value.toFixed(2)}{" "}
                <span className="text-xs font-normal">{f.unit}</span>
              </p>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2 mt-8 mb-4 text-xs text-secondary">
          <Quote size={14} />
          Supporting examples · {finding.evidence_ids.length} source messages
        </div>
        {loading && (
          <p role="status" className="text-sm">
            Loading source messages…
          </p>
        )}
        {error && (
          <p role="alert" className="text-red-600 text-sm">
            {error}
          </p>
        )}
        <div className="space-y-3">
          {items.map((m) => (
            <article
              key={m.id}
              className={`chat-bubble ${m.sender_id === me ? "chat-mine" : ""}`}
            >
              <div className="flex flex-wrap justify-between gap-2">
                <span className="text-xs font-semibold">
                  {m.sender_name || "System"}
                </span>
                <time className="text-[10px] text-secondary">
                  {date(m.timestamp, true)} · UTC
                </time>
              </div>
              <p className="text-sm whitespace-pre-wrap break-words leading-relaxed mt-3">
                {m.text || `[${m.message_type}]`}
              </p>
              <button
                className="text-xs text-accent flex gap-1 items-center mt-3"
                onClick={() => void context(m.id)}
              >
                Nearby messages
                <ChevronDown size={12} />
              </button>
              {contexts[m.id] && (
                <div className="mt-3 border-l-2 border-border pl-3 space-y-3">
                  {contexts[m.id].map((x) => (
                    <p
                      key={x.id}
                      className={`chat-bubble text-xs leading-relaxed ${x.sender_id === me ? "chat-mine" : ""} ${x.id === m.id ? "font-semibold" : "text-secondary"}`}
                    >
                      <span>
                        {x.sender_name || "System"} · {date(x.timestamp, true)}
                      </span>
                      <br />
                      {x.text || `[${x.message_type}]`}
                    </p>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      </div>
    </dialog>
  );
}
