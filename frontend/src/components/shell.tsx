"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import {
  Aperture,
  MessageSquare,
  Plus,
  Settings,
  ShieldCheck,
  ArrowUpRight,
} from "lucide-react";
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  useEffect(() => {
    const theme = localStorage.getItem("chatlens-theme") || "system";
    document.documentElement.classList.toggle(
      "dark",
      theme === "dark" ||
        (theme === "system" &&
          matchMedia("(prefers-color-scheme: dark)").matches),
    );
  }, []);
  return (
    <div className="min-h-screen md:pl-60">
      <aside className="md:fixed md:inset-y-0 md:left-0 md:w-60 bg-surface border-b md:border-r border-border flex flex-col z-20">
        <Link
          href="/"
          className="flex items-center gap-2.5 p-6 text-xl font-semibold tracking-tight"
        >
          <Aperture className="text-accent" size={26} />
          ChatLens<span className="ml-auto badge">local</span>
        </Link>
        <div className="px-5 pt-4 pb-2 eyebrow hidden md:block">
          Your little corner
        </div>
        <nav className="flex md:flex-col px-3 pb-3 gap-1">
          {[
            { href: "/", label: "Conversations", icon: MessageSquare },
            { href: "/import", label: "Import", icon: Plus },
            { href: "/settings", label: "Settings", icon: Settings },
          ].map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm ${pathname === href ? "bg-muted font-medium" : "text-secondary hover:bg-muted"}`}
            >
              <Icon size={17} />
              {label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto p-5 hidden md:block">
          <div className="border border-border rounded-lg p-3">
            <ShieldCheck size={17} className="text-emerald-600 mb-2" />
            <p className="text-xs font-medium">
              Your conversations stay yours.
            </p>
            <p className="prose-note mt-1">
              Local by default. No telemetry.
              <br />
              Gemini for chats you enable.
            </p>
          </div>
          <p className="text-[11px] text-secondary mt-4 flex justify-between">
            ChatLens · Discoveries <ArrowUpRight size={12} />
          </p>
        </div>
      </aside>
      <header className="h-16 border-b border-border flex items-center justify-between px-6 lg:px-10 text-xs text-secondary">
        <span>
          Your scrapbook <span className="mx-3 opacity-40">/</span>{" "}
          {pathname === "/import"
            ? "Import"
            : pathname === "/settings"
              ? "Settings"
              : pathname.startsWith("/conversation/")
                ? "Conversation"
                : "Conversations"}
        </span>
        <span className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Made for your moments
        </span>
      </header>
      <main className="max-w-[1440px] mx-auto p-5 lg:p-10">{children}</main>
    </div>
  );
}
