"use client";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { AISettings } from "@/components/ai-settings";
export default function Settings() {
  const [tab, setTab] = useState("Preferences");
  const [gap, setGap] = useState("4");
  const [theme, setTheme] = useState("system");
  const [format, setFormat] = useState("locale");
  const [tone, setTone] = useState("fun");
  const [zone, setZone] = useState("UTC");
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    setTone(localStorage.getItem("chatlens-tone") || "fun");
    setZone(localStorage.getItem("chatlens-timezone") || "UTC");
    setGap(localStorage.getItem("chatlens-gap") || "4");
    setTheme(localStorage.getItem("chatlens-theme") || "system");
    setFormat(localStorage.getItem("chatlens-date") || "locale");
  }, []);
  function save() {
    localStorage.setItem("chatlens-tone", tone);
    localStorage.setItem("chatlens-timezone", zone);
    localStorage.setItem("chatlens-gap", gap);
    localStorage.setItem("chatlens-theme", theme);
    localStorage.setItem("chatlens-date", format);
    document.documentElement.classList.toggle(
      "dark",
      theme === "dark" ||
        (theme === "system" &&
          matchMedia("(prefers-color-scheme: dark)").matches),
    );
    setSaved(true);
  }
  return (
    <div className="max-w-2xl">
      <p className="eyebrow mb-2">Make yourself at home</p>
      <h1>Settings</h1>
      <p className="text-secondary text-sm mt-2 mb-8">
        Preferences are stored in this browser.
      </p>
      <div
        role="tablist"
        aria-label="Settings sections"
        className="flex gap-3 mb-5"
      >
        {["Preferences", "AI & LLM"].map((t) => (
          <Button
            key={t}
            role="tab"
            aria-selected={tab === t}
            variant={tab === t ? "default" : "outline"}
            onClick={() => setTab(t)}
          >
            {t}
          </Button>
        ))}
      </div>
      {tab === "AI & LLM" && <AISettings />}
      <form
        hidden={tab !== "Preferences"}
        className="card space-y-6"
        onSubmit={(e) => {
          e.preventDefault();
          save();
        }}
      >
        <div>
          <label htmlFor="gap" className="block text-sm font-medium mb-2">
            Default session gap (hours)
          </label>
          <input
            id="gap"
            type="number"
            min="0.1"
            max="168"
            step="0.1"
            required
            value={gap}
            onChange={(e) => {
              setGap(e.target.value);
              setSaved(false);
            }}
          />
          <p className="prose-note mt-2">
            A longer gap starts a new session. Applied when you open a
            conversation.
          </p>
        </div>
        <div>
          <label htmlFor="format" className="block text-sm font-medium mb-2">
            Date/time display
          </label>
          <select
            id="format"
            value={format}
            onChange={(e) => setFormat(e.target.value)}
          >
            <option value="locale">Browser locale · UTC</option>
            <option value="iso">Year-month-day · UTC</option>
          </select>
        </div>
        <div>
          <label htmlFor="theme" className="block text-sm font-medium mb-2">
            Theme
          </label>
          <select
            id="theme"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
          >
            <option value="system">System</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </div>
        <div>
          <label htmlFor="tone" className="block text-sm font-medium mb-2">
            Analysis tone
          </label>
          <select
            id="tone"
            value={tone}
            onChange={(e) => setTone(e.target.value)}
          >
            <option value="fun">Fun (default)</option>
            <option value="balanced">Balanced</option>
            <option value="analytical">Analytical</option>
          </select>
          <p className="prose-note mt-2">
            The same measurements, a different reading mood.
          </p>
        </div>
        <div>
          <label htmlFor="timezone" className="block text-sm font-medium mb-2">
            Report timezone
          </label>
          <select
            id="timezone"
            value={zone}
            onChange={(e) => setZone(e.target.value)}
          >
            {[
              "UTC",
              "Asia/Kolkata",
              "Europe/London",
              "Europe/Paris",
              "America/New_York",
              "America/Los_Angeles",
              "Asia/Tokyo",
              "Australia/Sydney",
            ].map((z) => (
              <option key={z} value={z}>
                {z}
              </option>
            ))}
          </select>
          <p className="prose-note mt-2">
            New WhatsApp imports use the timezone you choose during upload.
            Older imports without a saved timezone retain UTC wall time. Raw
            message timestamps remain labelled in UTC.
          </p>
        </div>
        <Button type="submit">Save preferences</Button>
        {saved && (
          <p role="status" className="text-sm text-emerald-600">
            Preferences saved.
          </p>
        )}
      </form>
    </div>
  );
}
