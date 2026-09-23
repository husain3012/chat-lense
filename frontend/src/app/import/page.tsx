"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, Check, ArrowRight, ShieldCheck, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, date, number } from "@/lib/api";
import type { Preview } from "@/lib/types";
export default function Import() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState(1);
  const [platform, setPlatform] = useState("whatsapp");
  const [confidence, setConfidence] = useState(0);
  const [order, setOrder] = useState("auto");
  const [chatTimezone, setChatTimezone] = useState("");
  const [chats, setChats] = useState<Preview[]>([]);
  const [selected, setSelected] = useState(0);
  const [me, setMe] = useState<number[]>([]);
  const [kind, setKind] = useState<"direct" | "group">("direct");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [aiConsent, setAiConsent] = useState(false);
  const chat = chats[selected];
  function form() {
    const f = new FormData();
    if (file) f.append("file", file);
    f.append("platform", platform);
    f.append("date_order", order);
    if (platform === "whatsapp") f.append("chat_timezone", chatTimezone);
    return f;
  }
  async function run(action: () => Promise<void>, label: string) {
    setError("");
    setBusy(label);
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function detect() {
    if (!file) return;
    const data = await api<{ platform: string | null; confidence: number }>(
      "/import/detect",
      { method: "POST", body: form() },
    );
    setPlatform(data.platform || "whatsapp");
    setConfidence(data.confidence);
    setStep(2);
  }
  async function preview() {
    const data = await api<{ conversations: Preview[] }>("/import/preview", {
      method: "POST",
      body: form(),
    });
    setChats(data.conversations);
    setSelected(0);
    setMe([]);
    setKind(data.conversations[0].conversation_type);
    setStep(3);
  }
  async function save() {
    const f = form();
    f.append("selection_index", String(selected));
    f.append("current_user_indices", me.join(","));
    f.append("conversation_type", kind);
    f.append("ai_consent", String(aiConsent));
    const result = await api<{ id: string }>("/import", {
      method: "POST",
      body: f,
    });
    router.push("/conversation/" + result.id);
  }
  return (
    <div className="max-w-3xl mx-auto">
      <p className="eyebrow mb-2">Bring your own history</p>
      <h1>Import a conversation</h1>
      <p className="text-secondary text-sm mt-2">
        One export. Your story, rediscovered. Choose local-only or Gemini
        analysis.
      </p>
      <ol className="flex justify-between my-9">
        {["Upload", "Detect", "Preview", "Your identity"].map((label, i) => (
          <li
            key={label}
            className={`flex items-center gap-2 text-xs ${step === i + 1 ? "text-accent" : "text-secondary"}`}
          >
            <span
              className={`w-6 h-6 rounded-full border flex items-center justify-center ${step > i + 1 ? "bg-accent text-white border-accent" : "border-border"}`}
            >
              {step > i + 1 ? <Check size={12} /> : i + 1}
            </span>
            <span className="hidden sm:inline">{label}</span>
          </li>
        ))}
      </ol>
      <div className="card">
        {step === 1 && (
          <>
            <h2 className="mb-4">Choose your exported chat</h2>
            <label className="flex items-start gap-3 p-4 bg-muted rounded-xl mb-5 text-sm">
              <input
                type="checkbox"
                checked={aiConsent}
                onChange={(e) => setAiConsent(e.target.checked)}
              />
              <span>
                Automatically analyze with Gemini after import. I agree to send
                original messages and participant names to Google Gemini for
                this conversation’s analysis and follow-up questions. Processing
                continues on the server and API usage costs apply. Leave
                unchecked for local statistics only.
              </span>
            </label>
            <label className="flex flex-col items-center justify-center border-2 border-dashed border-border rounded-xl px-5 py-12 cursor-pointer hover:border-accent">
              <Upload className="text-accent mb-4" />
              <span className="font-medium text-sm">
                {file?.name || "Choose a file to get started"}
              </span>
              <span className="prose-note mt-2">
                TXT, JSON, ZIP, or macOS chat.db · up to 100 MB by default
              </span>
              <input
                aria-label="Chat export"
                type="file"
                accept=".txt,.json,.zip,.db,.sqlite,.sqlite3"
                className="mt-5 text-xs"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <p className="prose-note mt-5">
              For folders, create a ZIP. Instagram exports and iMessage
              databases can contain several conversations; you’ll choose one in
              the preview.
            </p>
          </>
        )}
        {step === 2 && (
          <>
            <h2>Confirm the source</h2>
            <p className="text-sm text-secondary mt-2 mb-6">
              Detected platform:{" "}
              <span className="capitalize text-foreground">
                {confidence ? platform : "Unknown"}
              </span>{" "}
              · Confidence:{" "}
              {confidence >= 0.9
                ? "High"
                : confidence
                  ? "Medium"
                  : "Unavailable"}
            </p>
            <label className="block text-sm mb-2" htmlFor="platform">
              Platform
            </label>
            <select
              id="platform"
              className="w-full"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
            >
              {["whatsapp", "telegram", "instagram", "imessage"].map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            {platform === "whatsapp" && (
              <>
                <label
                  htmlFor="chat-timezone"
                  className="block text-sm mt-5 mb-2"
                >
                  What timezone was this chat exported in?
                </label>
                <input
                  id="chat-timezone"
                  className="w-full"
                  list="chat-timezones"
                  placeholder="Choose or enter a timezone, e.g. Asia/Kolkata"
                  value={chatTimezone}
                  onChange={(e) => setChatTimezone(e.target.value)}
                  required
                />
                <datalist id="chat-timezones">
                  {[
                    "UTC",
                    "Asia/Kolkata",
                    "Asia/Dubai",
                    "Asia/Singapore",
                    "Asia/Tokyo",
                    "Europe/London",
                    "Europe/Paris",
                    "America/New_York",
                    "America/Chicago",
                    "America/Denver",
                    "America/Los_Angeles",
                    "Australia/Sydney",
                  ].map((z) => (
                    <option key={z} value={z} />
                  ))}
                </datalist>
                <p className="prose-note mt-2">
                  WhatsApp doesn’t include a timezone. Choose the timezone used
                  by the exporting phone, so late-night habits and dates are
                  interpreted correctly.
                </p>
                <label htmlFor="date-order" className="block text-sm mt-5 mb-2">
                  Date order
                </label>
                <select
                  id="date-order"
                  className="w-full"
                  value={order}
                  onChange={(e) => setOrder(e.target.value)}
                >
                  <option value="auto">
                    Auto-detect (day first when ambiguous)
                  </option>
                  <option value="dmy">Day / month / year</option>
                  <option value="mdy">Month / day / year</option>
                </select>
              </>
            )}
          </>
        )}
        {step === 3 && chat && (
          <>
            {chats.length > 1 && (
              <select
                aria-label="Conversation to import"
                className="w-full mb-5"
                value={selected}
                onChange={(e) => {
                  const i = Number(e.target.value);
                  setSelected(i);
                  setMe([]);
                  setKind(chats[i].conversation_type);
                }}
              >
                {chats.map((c, i) => (
                  <option key={c.id} value={i}>
                    {c.title} ({number(c.message_count)} messages)
                  </option>
                ))}
              </select>
            )}
            <div className="flex justify-between mb-6">
              <div>
                <p className="eyebrow mb-2">Conversation preview</p>
                <h2 className="text-xl">{chat.title}</h2>
              </div>
              <span className="badge h-fit">{chat.platform}</span>
            </div>
            <div className="grid grid-cols-2 gap-6 mb-6">
              <div>
                <p className="text-2xl font-semibold">
                  {number(chat.message_count)}
                </p>
                <p className="prose-note">Messages</p>
              </div>
              <div>
                <p className="text-2xl font-semibold">
                  {chat.participants.length}
                </p>
                <p className="prose-note">Participants</p>
              </div>
            </div>
            <p className="text-sm mb-4">
              {date(chat.started_at)} — {date(chat.ended_at)}
            </p>
            <label htmlFor="kind" className="text-sm mr-3">
              Conversation type
            </label>
            <select
              id="kind"
              value={kind}
              onChange={(e) => setKind(e.target.value as "direct" | "group")}
            >
              <option value="direct">Direct</option>
              <option value="group">Group</option>
            </select>
            <p className="prose-note mt-2">
              Participant count and export metadata guide detection. Adjust if a
              group has only two visible senders.
            </p>
            <div className="flex flex-wrap gap-2 mt-5">
              {chat.participants.map((p) => (
                <span className="badge" key={p.id}>
                  {p.display_name}
                </span>
              ))}
            </div>
            {chat.warnings.map((w) => (
              <p key={w} className="prose-note bg-muted p-3 rounded-lg mt-4">
                {w}
              </p>
            ))}
          </>
        )}
        {step === 4 && chat && (
          <>
            <h2 className="text-xl mb-2">Which participant are you?</h2>
            <p className="text-sm text-secondary mb-6">
              Select every name that represents you. Aliases will be merged into
              one person, using the name with the most messages.
            </p>
            <div className="space-y-2">
              {chat.participants.map((p, i) => (
                <label
                  key={p.id}
                  className={`flex items-center gap-3 border rounded-lg p-4 cursor-pointer ${me.includes(i) ? "border-accent bg-accent/5" : "border-border"}`}
                >
                  <input
                    type="checkbox"
                    name="identity"
                    checked={me.includes(i)}
                    onChange={(event) =>
                      setMe(
                        event.target.checked
                          ? [...me, i]
                          : me.filter((value) => value !== i),
                      )
                    }
                  />
                  <span className="text-sm">{p.display_name}</span>
                </label>
              ))}
            </div>
          </>
        )}
        {error && (
          <p role="alert" className="text-red-600 text-sm mt-6">
            {error}
          </p>
        )}
        <div className="flex justify-between items-center mt-8 border-t border-border pt-5">
          <Button
            variant="ghost"
            disabled={step === 1 || !!busy}
            onClick={() => setStep(step - 1)}
          >
            Back
          </Button>
          <Button
            disabled={
              !!busy ||
              (step === 1 && !file) ||
              (step === 2 && platform === "whatsapp" && !chatTimezone.trim()) ||
              (step === 4 && me.length === 0)
            }
            onClick={() => {
              if (step === 1) void run(detect, "Detecting…");
              else if (step === 2) void run(preview, "Parsing export…");
              else if (step === 3) setStep(4);
              else void run(save, "Importing messages…");
            }}
          >
            {busy ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                {busy}
              </>
            ) : (
              <>
                {step === 4 ? "Import conversation" : "Continue"}
                <ArrowRight size={16} />
              </>
            )}
          </Button>
        </div>
      </div>
      <p className="prose-note flex items-center justify-center gap-2 mt-6">
        <ShieldCheck size={14} />
        Temporary upload files are deleted after processing.
      </p>
    </div>
  );
}
