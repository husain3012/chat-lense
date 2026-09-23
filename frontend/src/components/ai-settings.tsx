"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
type Config = {
  configured: boolean;
  model: string;
  interval_seconds: number;
  max_retries: number;
  input_budget: number;
  output_tokens: number;
  chunk_messages: number;
};
export function AISettings() {
  const [config, setConfig] = useState<Config | null>(null);
  const [key, setKey] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api<Config>("/settings/ai")
      .then(setConfig)
      .catch((e) => setNotice(e.message));
  }, []);
  async function save() {
    if (!config) return;
    setBusy(true);
    setNotice("");
    try {
      setConfig(
        await api<Config>("/settings/ai", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...config, api_key: key || undefined }),
        }),
      );
      setKey("");
      setNotice("Saved. The worker uses these settings for its next call.");
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form
      className="card space-y-5"
      onSubmit={(e) => {
        e.preventDefault();
        void save();
      }}
    >
      <h2>✨ Gemini & processing</h2>
      <p className="prose-note">
        Server settings are shared by this installation. A key set here
        overrides .env and is stored in your local database; it is never
        returned to the browser. Keep this unauthenticated app on localhost.
      </p>
      {config && (
        <>
          <label className="block text-sm">
            API key · {config.configured ? "configured" : "not configured"}
            <input
              className="block w-full mt-2"
              type="password"
              autoComplete="new-password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="Leave blank to keep the existing key"
            />
          </label>
          <label className="block text-sm">
            Gemini model
            <input
              className="block w-full mt-2"
              value={config.model}
              required
              pattern="[A-Za-z0-9._-]+"
              onChange={(e) => setConfig({ ...config, model: e.target.value })}
            />
          </label>
          {(
            [
              [
                "interval_seconds",
                "Minimum seconds between worker calls",
                1,
                3600,
              ],
              [
                "max_retries",
                "Retries for rate limits and temporary failures",
                0,
                20,
              ],
              [
                "input_budget",
                "Conservative input budget (UTF-8 bytes, including context)",
                12000,
                500000,
              ],
              ["output_tokens", "Maximum output tokens per call", 2048, 32768],
              ["chunk_messages", "Maximum messages per passage", 20, 5000],
            ] as const
          ).map(([field, label, min, max]) => (
            <label key={field} className="block text-sm">
              {label}
              <input
                className="block mt-2"
                type="number"
                min={min}
                max={max}
                required
                value={config[field]}
                onChange={(e) =>
                  setConfig({ ...config, [field]: Number(e.target.value) })
                }
              />
            </label>
          ))}
          <p className="prose-note">
            All eligible messages are visited in chronological order with
            overlap. Oversized messages are truncated to 2,000 characters and
            counted in coverage. Retries use exponential backoff. Choose budgets
            within your model’s limits. Long histories can take hours and incur
            many calls.
          </p>
          <Button disabled={busy}>
            {busy ? "Saving…" : "Save AI settings"}
          </Button>
        </>
      )}
      {notice && (
        <p role="status" className="text-sm">
          {notice}
        </p>
      )}
    </form>
  );
}
