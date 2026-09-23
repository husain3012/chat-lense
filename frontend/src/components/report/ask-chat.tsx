"use client";
import { useEffect, useRef, useState } from "react";
import { ThinkingOrb } from "thinking-orbs";
import { api } from "@/lib/api";
import type { Finding } from "@/lib/report-types";
import { Button } from "@/components/ui/button";

export function AskChat({
  id,
  finding,
  onClose,
  onEvidence,
}: {
  id: string;
  finding?: Finding;
  onClose: () => void;
  onEvidence: (f: Finding) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [text, setText] = useState("");
  const [turns, setTurns] = useState<
    { role: string; text: string; evidence_ids?: string[] }[]
  >([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  async function send() {
    if (!text.trim() || busy) return;
    const question = text;
    setBusy(true);
    setError("");
    setText("");
    setTurns((t) => [...t, { role: "user", text: question }]);
    try {
      const answer = await api<{ answer: string; evidence_ids: string[] }>(
        `/conversations/${id}/ask`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question,
            finding_id: finding?.id,
            history: turns.slice(-6),
          }),
        },
      );
      setTurns((t) => [
        ...t,
        {
          role: "assistant",
          text: answer.answer,
          evidence_ids: answer.evidence_ids,
        },
      ]);
    } catch (e) {
      setError((e as Error).message);
      setText(question);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      onCancel={onClose}
      className="evidence-dialog bg-surface text-foreground rounded-2xl p-6"
      aria-label="Ask about your chat"
    >
      <div className="flex justify-between gap-4">
        <h2 className="text-xl">
          💬 {finding ? `About “${finding.title}”` : "Ask your chat"}
        </h2>
        <Button variant="ghost" onClick={onClose}>
          Close
        </Button>
      </div>
      <p className="prose-note my-4">
        Gemini searches this conversation and nearby exchanges. Answers are
        interpretations of retrieved evidence, not a verdict on either person.
      </p>
      <div
        className="space-y-4 max-h-[50vh] overflow-y-auto"
        aria-live="polite"
      >
        {turns.map((turn, i) => (
          <article
            key={i}
            className={`chat-bubble ${turn.role === "user" ? "chat-mine" : ""}`}
          >
            <p className="whitespace-pre-wrap text-sm">{turn.text}</p>
            {!!turn.evidence_ids?.length && (
              <button
                className="text-accent text-xs mt-3"
                onClick={() =>
                  onEvidence({
                    ...(finding || {}),
                    id: "answer",
                    title: "Sources behind this answer",
                    description: turn.text,
                    evidence_ids: turn.evidence_ids!,
                    facts: [],
                    method: "Scoped text retrieval with surrounding messages.",
                    caveat:
                      "Search does not cover every possible relevant exchange.",
                  } as Finding)
                }
              >
                Read supporting messages →
              </button>
            )}
          </article>
        ))}
      </div>
      {busy && (
        <div className="flex gap-3 items-center mt-5" role="status">
          <ThinkingOrb state="searching" size={20} /> Looking through the
          context…
        </div>
      )}
      {error && (
        <p role="alert" className="text-red-600 text-sm mt-4">
          {error}
        </p>
      )}
      <form
        className="flex gap-2 mt-5"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          aria-label="Question about this chat"
          placeholder="What was happening around this moment?"
          className="flex-1 min-w-0"
          maxLength={2000}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <Button disabled={busy || !text.trim()}>Ask</Button>
      </form>
    </dialog>
  );
}
