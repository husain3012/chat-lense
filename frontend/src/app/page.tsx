"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Plus, MessageSquare, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, date, number } from "@/lib/api";
import type { Conversation } from "@/lib/types";
export default function Home() {
  const [data, setData] = useState<{
    items: Conversation[];
    total: number;
  } | null>(null);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => {
    api<{ items: Conversation[]; total: number }>(`/conversations?page=${page}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [page]);
  return (
    <>
      <section className="library-hero">
        <div className="sticker-stack" aria-hidden="true">
          <span>💌</span>
          <span>😂</span>
          <span>🫶</span>
          <span>🪩</span>
          <span>🌱</span>
        </div>
        <p className="eyebrow">Every chat has a little lore</p>
        <h1>
          All those messages.
          <br />
          <em>So much more between them.</em>
        </h1>
        <p>
          The in-jokes. The midnight essays. The “you had to be there” moments.
          <br className="hidden sm:block" /> Meet your conversations from a
          whole new angle.
        </p>
        <Button asChild>
          <Link href="/import">
            <Plus size={17} />
            Unwrap a conversation <ArrowRight size={17} />
          </Link>
        </Button>
        <div className="library-tags">
          <span>🫶 Best friends</span>
          <span>💞 Your person</span>
          <span>🏡 Family lore</span>
          <span>🪩 The group chat</span>
        </div>
      </section>
      <div className="flex items-start justify-between gap-4 mb-8">
        <div>
          <p className="eyebrow mb-2">Your little collection</p>
          <h2 className="text-2xl font-semibold">
            Conversations worth keeping
          </h2>
          <p className="text-secondary text-sm mt-2">
            Pick a chat. There’s probably something you never noticed.
          </p>
        </div>
        <Button asChild>
          <Link href="/import">
            <Plus size={16} />
            Import chat
          </Link>
        </Button>
      </div>
      <div className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3 mb-8 text-xs text-secondary">
        <ShieldCheck size={17} className="text-emerald-600" />A private space
        for your messages. Local insights first. Optional Gemini analysis is
        always your choice.
      </div>
      <div className="flex items-center justify-between mb-4">
        <h2>
          All conversations{" "}
          <span className="ml-2 text-secondary font-normal">
            {data?.total ?? "—"}
          </span>
        </h2>
        <span className="eyebrow">Latest activity</span>
      </div>
      {error && (
        <p role="alert" className="card text-red-600">
          {error}
        </p>
      )}
      {!data && !error && (
        <p className="card text-secondary">Loading conversations…</p>
      )}
      {data?.total === 0 ? (
        <div className="card py-20 flex flex-col items-center text-center">
          <div className="p-4 rounded-xl bg-muted mb-5">
            <MessageSquare size={28} className="text-accent" />
          </div>
          <h2 className="text-lg">A new view of your conversations</h2>
          <p className="text-secondary text-sm max-w-md mt-2 mb-6">
            Import a chat to explore activity, participation, and the rhythm of
            your messages.
          </p>
          <Button asChild>
            <Link href="/import">
              Import your first chat
              <ArrowRight size={16} />
            </Link>
          </Button>
          <p className="prose-note mt-6">
            WhatsApp · Telegram · Instagram · iMessage
          </p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-4">
          {data?.items.map((c, i) => (
            <Link
              href={`/conversation/${c.id}`}
              key={c.id}
              className={`card library-chat library-chat-${i % 4} hover:border-accent transition-colors group`}
            >
              <div className="flex items-center gap-3 mb-6">
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center ${i % 2 ? "bg-blue-500/10 text-blue-500" : "bg-violet-500/10 text-violet-500"}`}
                >
                  <span className="text-2xl" aria-hidden="true">
                    {["💌", "🫧", "🌷", "🍋"][i % 4]}
                  </span>
                </div>
                <div className="min-w-0">
                  <h2 className="truncate">{c.title}</h2>
                  <p className="text-xs text-secondary capitalize mt-1">
                    {c.platform}
                  </p>
                </div>
                <span className="badge ml-auto">{c.conversation_type}</span>
              </div>
              <div className="flex items-end justify-between">
                <div>
                  <p className="text-2xl font-semibold tracking-tight">
                    {number(c.message_count)}{" "}
                    <span className="text-xs text-secondary font-normal">
                      messages
                    </span>
                  </p>
                  <p className="text-xs text-secondary mt-2">
                    {date(c.started_at)} — {date(c.ended_at)}
                  </p>
                </div>
                <ArrowRight
                  size={18}
                  className="text-secondary group-hover:text-accent"
                />
              </div>
            </Link>
          ))}
        </div>
      )}
      {data && data.total > 50 && (
        <div className="flex gap-3 mt-5">
          <Button disabled={page === 1} onClick={() => setPage(page - 1)}>
            Previous
          </Button>
          <Button
            disabled={page * 50 >= data.total}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </>
  );
}
