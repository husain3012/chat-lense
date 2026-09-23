"use client";
import { ArrowUpRight, Download, Quote, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Finding } from "@/lib/report-types";
import { createCard } from "./share";
import { momentStyles, sticker } from "./moment-style";
import { useChatContext } from "./chat-context";

function SharePreview({
  image,
  onClose,
}: {
  image: string;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  return createPortal(
    <dialog
      ref={dialog}
      onCancel={onClose}
      className="evidence-dialog"
      aria-label="Preview share card"
    >
      <div className="p-5 space-y-4">
        <div className="flex justify-between gap-4 items-center">
          <h2 className="text-xl">Your discovery, ready to share</h2>
          <button onClick={onClose} aria-label="Close share preview">
            Close
          </button>
        </div>
        <p className="text-sm text-secondary">
          Review names and finding text before sharing. This image is created
          locally.
        </p>
        {/* A local canvas data URL; no image service or external request. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={image}
          alt="Preview of the selected ChatLens discovery card"
          className="w-full rounded-xl"
        />
        <a
          href={image}
          download="chatlens-discovery.png"
          className="inline-block rounded-lg bg-violet-600 text-white px-4 py-2"
        >
          Download PNG
        </a>
        <p className="text-xs text-secondary">
          If your in-app browser blocks downloads, open ChatLens in your regular
          browser.
        </p>
      </div>
    </dialog>,
    document.body,
  );
}

export function MiniVisual({ finding }: { finding: Finding }) {
  const points = finding.visual.slice(0, 8);
  const max = Math.max(1, ...points.map((p) => p.value));
  if (!points.length) return null;
  return (
    <div className="space-y-2.5 mt-5" aria-label="Supporting comparison">
      {points.map((p, i) => (
        <div
          key={p.label + "-" + i}
          className="grid grid-cols-[minmax(0,1fr)_minmax(50px,1.2fr)_auto] items-center gap-3"
        >
          <span className="truncate text-[11px] opacity-75" title={p.label}>
            {p.label}
          </span>
          <div className="h-1.5 rounded-full bg-current/10 overflow-hidden">
            <div
              className="h-full rounded-full bg-current opacity-70"
              style={{ width: `${(Math.max(0, p.value) / max) * 100}%` }}
            />
          </div>
          <span className="text-xs tabular-nums">
            {Number.isInteger(p.value)
              ? p.value.toLocaleString()
              : p.value.toFixed(1)}
          </span>
        </div>
      ))}
    </div>
  );
}
export function FindingCard({
  finding,
  onEvidence,
  title,
  hero = false,
  compact = false,
  person,
}: {
  finding: Finding;
  onEvidence: (f: Finding) => void;
  title: string;
  hero?: boolean;
  compact?: boolean;
  person?: string;
}) {
  const chat = useChatContext();
  const mood =
    momentStyles[finding.moment_kind || "connection"] ||
    momentStyles.connection;
  const [error, setError] = useState("");
  const [shareImage, setShareImage] = useState("");
  return (
    <article
      id={"finding-" + finding.id}
      className={`discovery-card ${finding.source === "ai" ? "moment-card moment-" + (finding.moment_kind || "connection") : "habit-card"} ${hero ? "discovery-hero" : ""} ${compact ? "discovery-compact" : ""}`}
    >
      <div className="card-sticker" aria-hidden="true">
        {finding.source === "ai" ? mood.emoji : sticker(finding.category)}
      </div>
      <div className="flex justify-between items-center gap-3">
        <span className="text-[10px] font-semibold uppercase tracking-[.16em] opacity-65">
          {person || (finding.source === "ai" ? mood.label : finding.category)}
        </span>
        <span className="flex items-center gap-1 text-[10px] opacity-60">
          {finding.source === "ai" ? (
            <>
              <Sparkles size={11} />A reading
            </>
          ) : finding.interpretation ? (
            "From your chat"
          ) : (
            "Counted locally"
          )}
        </span>
      </div>
      <h3
        className={`${hero ? "text-3xl sm:text-4xl" : "text-xl"} font-semibold tracking-tight mt-4 leading-tight`}
      >
        {finding.title}
      </h3>
      <div
        className={`${hero ? "text-6xl sm:text-7xl" : "text-4xl"} font-semibold tracking-[-.05em] mt-5 leading-none ${finding.source === "ai" ? "hidden" : ""}`}
      >
        {finding.value}
      </div>
      {finding.source !== "ai" && (
        <p className="text-xs mt-2 opacity-65">{finding.label}</p>
      )}
      {!!finding.source_quotes?.length && (
        <div
          className="moment-exchange"
          aria-label="Original conversation excerpts"
        >
          {finding.source_quotes.slice(0, 3).map((q, n) => (
            <blockquote
              key={q.message_id + n}
              className={
                (
                  q.sender_id
                    ? q.sender_id === chat.me
                    : q.sender_name === chat.meName
                )
                  ? "quote-bubble quote-reply"
                  : "quote-bubble"
              }
            >
              <span className="quote-person">
                {q.sender_name}{" "}
                <time dateTime={q.timestamp} className="font-normal opacity-65">
                  ·{" "}
                  {new Date(q.timestamp).toLocaleString(undefined, {
                    month: "short",
                    year: "numeric",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                    timeZone: "UTC",
                  })}{" "}
                  UTC
                </time>
              </span>
              <p dir="auto">{q.text}</p>
            </blockquote>
          ))}
        </div>
      )}
      <p
        className={`${hero ? "text-base max-w-xl" : "text-sm"} leading-relaxed mt-5 opacity-85`}
      >
        {finding.description}
      </p>
      {!compact && <MiniVisual finding={finding} />}
      {chat.ask && (
        <button
          className="text-xs text-accent mt-4"
          onClick={() => chat.ask?.(finding)}
        >
          💬 Ask about this
        </button>
      )}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-current/10 gap-3">
        <button
          onClick={() => onEvidence(finding)}
          className="text-xs font-medium inline-flex items-center gap-2 hover:underline"
        >
          <Quote size={13} />
          Revisit this moment
          <ArrowUpRight size={12} />
        </button>
        <button
          aria-label={`Save card: ${finding.title}`}
          title="Save a local image card with names and finding text; review before sharing"
          className="opacity-60 hover:opacity-100"
          onClick={() => {
            try {
              setShareImage(createCard(finding, title));
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          <Download size={15} />
        </button>
      </div>
      {error && (
        <p role="alert" className="text-xs mt-2">
          {error}
        </p>
      )}
      {shareImage && (
        <SharePreview image={shareImage} onClose={() => setShareImage("")} />
      )}
    </article>
  );
}
