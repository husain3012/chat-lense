"use client";
import { useEffect, useRef, useState } from "react";
import {
  Download,
  Film,
  FileText,
  X,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { ChatReport, Finding } from "@/lib/report-types";

export function ExportWrap({
  id,
  report,
  findings,
  onClose,
}: {
  id: string;
  report: ChatReport;
  findings: Finding[];
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [chosen, setChosen] = useState(
    findings
      .filter((f) => f.source !== "ai")
      .slice(0, 4)
      .map((f) => f.id),
  );
  const [title, setTitle] = useState("Our chat, wrapped.");
  const [aliases, setAliases] = useState(true);
  const [verdict, setVerdict] = useState(false);
  const [palette, setPalette] = useState("peach");
  const [seconds, setSeconds] = useState(6);
  const [preview, setPreview] = useState<{
    pages: string[];
    count: number;
    duration: number;
  } | null>(null);
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState<"mp4" | "pdf" | null>(null);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{
    url: string;
    format: "mp4" | "pdf";
  } | null>(null);
  const resultUrl = useRef<string | null>(null);
  const payload = JSON.stringify({
    finding_ids: chosen,
    aliases,
    include_verdict: verdict,
    title,
    palette,
    seconds_per_slide: seconds,
  });
  useEffect(() => {
    const d = dialog.current;
    d?.showModal();
    return () => {
      d?.close();
      if (resultUrl.current) URL.revokeObjectURL(resultUrl.current);
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setPreview(null);
    setError("");
    setPage(0);
    setResult(null);
    if (resultUrl.current) {
      URL.revokeObjectURL(resultUrl.current);
      resultUrl.current = null;
    }
    const timer = setTimeout(() => {
      api<{ pages: string[]; count: number; duration: number }>(
        `/conversations/${id}/export/preview`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
          signal: controller.signal,
        },
      )
        .then(setPreview)
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [id, payload]);
  async function download(format: "mp4" | "pdf") {
    setBusy(format);
    setError("");
    setResult(null);
    try {
      const response = await fetch(
        `/api/conversations/${id}/export/${format}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
        },
      );
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail || "Export failed. Please retry.");
      }
      const blob = await response.blob();
      if (resultUrl.current) URL.revokeObjectURL(resultUrl.current);
      const url = URL.createObjectURL(blob);
      resultUrl.current = url;
      setResult({ url, format });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed. Please retry.");
    } finally {
      setBusy(null);
    }
  }
  return (
    <dialog
      ref={dialog}
      className="wrap-dialog"
      aria-labelledby="wrap-title"
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else onClose();
      }}
    >
      <div className="flex justify-between items-start gap-4 mb-6">
        <div>
          <p className="eyebrow">A story worth keeping 💌</p>
          <h2 id="wrap-title" className="text-3xl font-bold mt-2">
            Your chat. The highlight reel.
          </h2>
          <p className="text-sm text-secondary mt-2">
            Pick the bits you love. Preview every page. Make it yours.
          </p>
        </div>
        <button aria-label="Close export" disabled={!!busy} onClick={onClose}>
          <X />
        </button>
      </div>
      <div className="wrap-studio">
        <div className="wrap-controls">
          <fieldset disabled={!!busy} className="space-y-5">
            <label className="block text-sm font-semibold">
              Wrap title
              <input
                className="block w-full mt-2"
                value={title}
                maxLength={80}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <div>
              <p className="text-sm font-semibold mb-2">Choose a mood</p>
              <div className="flex gap-2">
                {["peach", "lilac", "mint"].map((p) => (
                  <button
                    key={p}
                    aria-pressed={palette === p}
                    onClick={() => setPalette(p)}
                    className={`wrap-swatch ${p} ${palette === p ? "selected" : ""}`}
                  >
                    {p === "peach" ? "🍑" : p === "lilac" ? "🪻" : "🌿"} {p}
                  </button>
                ))}
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={aliases}
                onChange={(e) => setAliases(e.target.checked)}
              />
              Use Person 1 / Person 2 instead of participant names
            </label>
            <p className="text-xs text-secondary">
              Aliases replace participant names, not every identifying detail.
              Review the pages before sharing. Private message excerpts may
              appear in selected AI findings.
            </p>
            {report.verdict && (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={verdict}
                  onChange={(e) => setVerdict(e.target.checked)}
                />
                Include the final relationship perspective
              </label>
            )}
            <div>
              <p className="text-sm font-semibold mb-2">
                The good bits · {chosen.length} selected
              </p>
              <div className="flex gap-3 text-xs text-accent mb-2">
                <button
                  onClick={() =>
                    setChosen(findings.slice(0, 50).map((f) => f.id))
                  }
                >
                  Select report highlights for PDF
                </button>
                <button onClick={() => setChosen([])}>Clear</button>
              </div>
              <p className="text-xs text-secondary mb-2">
                Up to 8 for video · 50 for PDF
              </p>
              <div className="wrap-picks">
                {findings.map((f) => (
                  <label
                    key={f.id}
                    className="flex items-start gap-3 py-3 border-b border-border text-sm"
                  >
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={chosen.includes(f.id)}
                      disabled={!chosen.includes(f.id) && chosen.length >= 50}
                      onChange={(e) =>
                        setChosen(
                          e.target.checked
                            ? [...chosen, f.id]
                            : chosen.filter((i) => i !== f.id),
                        )
                      }
                    />
                    <span>
                      {f.title}
                      <small className="block text-secondary mt-1">
                        {f.source === "ai"
                          ? "✨ AI interpretation"
                          : "📊 Measured from your chat"}
                      </small>
                    </span>
                  </label>
                ))}
              </div>
            </div>
            <label className="flex items-center gap-3 text-sm">
              Video pace
              <select
                value={seconds}
                onChange={(e) => setSeconds(Number(e.target.value))}
              >
                <option value={4}>Quick · 4s/page</option>
                <option value={6}>Easy · 6s/page</option>
                <option value={10}>Take your time · 10s/page</option>
              </select>
            </label>
          </fieldset>
        </div>
        <div className="wrap-preview-column">
          <div className="wrap-phone">
            {preview ? (
              <iframe
                title={`Wrap preview page ${page + 1}`}
                sandbox=""
                srcDoc={preview.pages[page]}
                scrolling="no"
              />
            ) : (
              <div className="p-8 text-center text-sm">
                Preparing your preview ✨
              </div>
            )}
          </div>
          {preview && (
            <div className="flex justify-center items-center gap-4 mt-4">
              <button
                aria-label="Previous preview page"
                disabled={page === 0}
                onClick={() => setPage(page - 1)}
              >
                <ChevronLeft />
              </button>
              <span className="text-xs">
                {page + 1} / {preview.count} · {preview.duration}s video
              </span>
              <button
                aria-label="Next preview page"
                disabled={page + 1 === preview.count}
                onClick={() => setPage(page + 1)}
              >
                <ChevronRight />
              </button>
            </div>
          )}
          <p className="text-xs text-secondary text-center mt-4">
            Portrait 9:16 · MP4 / H.264 · 720 × 1280
            <br />
            Silent video — add your own music when you post.
            <br />
            PDF contains the same selected pages.
          </p>
        </div>
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-500 mt-5">
          {error}
        </p>
      )}
      <div className="wrap-actions">
        <p className="text-xs text-secondary flex-1" aria-live="polite">
          {busy
            ? `Making your ${busy === "mp4" ? "movie" : "keepsake"}… Keep this window open. Larger wraps may take a few minutes.`
            : "Rendered locally. No new AI calls. Nothing is posted automatically."}
        </p>
        <Button
          disabled={!!busy || !preview}
          onClick={() => void download("pdf")}
        >
          <FileText size={16} />
          Make PDF
        </Button>
        <Button
          disabled={!!busy || !preview || chosen.length > 8}
          onClick={() => void download("mp4")}
        >
          <Film size={16} />
          Make my video
        </Button>
        {chosen.length > 8 && (
          <p className="text-xs text-secondary w-full">
            Choose eight or fewer highlights to enable video export.
          </p>
        )}
      </div>
      {result && (
        <div className="mt-6 rounded-2xl bg-muted p-5">
          <p className="font-semibold mb-3">It’s a wrap! 🎉</p>
          {result.format === "mp4" && (
            <video
              controls
              playsInline
              src={result.url}
              className="max-h-80 rounded-xl mb-4 mx-auto"
            />
          )}
          <a
            className="inline-flex items-center gap-2 text-accent font-semibold"
            download={`chatlens-wrap.${result.format}`}
            href={result.url}
          >
            <Download size={17} />
            Save {result.format.toUpperCase()}
          </a>
        </div>
      )}
    </dialog>
  );
}
