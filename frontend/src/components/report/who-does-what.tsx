"use client";

import { ArrowUpRight, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Finding } from "@/lib/report-types";
import type { Person } from "@/lib/types";
import {
  behaviorCards,
  personalityProfiles,
  type BehaviorCardData,
  type BehaviorData,
} from "@/lib/behavior-presentation";

function BehaviorDetails({
  card,
  onClose,
  onEvidence,
}: {
  card: BehaviorCardData;
  onClose: () => void;
  onEvidence: (title: string, description: string, ids: string[]) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const max = Math.max(1, ...card.ranked.map((person) => person.count));

  return createPortal(
    <dialog
      ref={dialog}
      className={`behavior-dialog behavior-tone-${card.tone}`}
      aria-labelledby={`behavior-title-${card.key}`}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClose={onClose}
    >
      <div className="behavior-dialog-top">
        <div className="behavior-dialog-emoji" aria-hidden="true">
          {card.emoji}
        </div>
        <button
          className="behavior-close"
          onClick={onClose}
          aria-label="Close comparison"
        >
          <X size={18} />
        </button>
      </div>
      <p className="eyebrow">A closer look</p>
      <h3 id={`behavior-title-${card.key}`}>{card.title}</h3>
      <p className="behavior-dialog-description">{card.description}</p>
      <div className="behavior-dialog-ranking">
        {card.ranked.map((person) => (
          <div className="behavior-person-row" key={person.id}>
            <div className="behavior-person-copy">
              <span>
                {person.display_name}
                {person.is_current_user ? " (you)" : ""}
              </span>
              <strong>{person.count.toLocaleString()}</strong>
            </div>
            <div className="behavior-meter" aria-hidden="true">
              <span style={{ width: `${(person.count / max) * 100}%` }} />
            </div>
            <div className="behavior-person-note">
              <span>{person.rate.toFixed(1)} per 100 messages</span>
              {!!person.evidence_ids.length && (
                <button
                  onClick={() => {
                    onClose();
                    onEvidence(
                      `${card.title} · ${person.display_name}`,
                      card.description,
                      person.evidence_ids,
                    );
                  }}
                >
                  Read examples <ArrowUpRight size={12} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      <p className="behavior-method-note">
        One count per tagged message, not per word or incident. Rates account
        for how much each person messages. Classification can still miss
        sarcasm or context, so the original conversation remains the best judge.
      </p>
    </dialog>,
    document.body,
  );
}

export function WhoDoesWhat({
  data,
  people,
  onEvidence,
}: {
  data: BehaviorData;
  people: Person[];
  onEvidence: (finding: Finding) => void;
}) {
  const [active, setActive] = useState<BehaviorCardData | null>(null);
  const cards = behaviorCards(data, people);
  const profiles = personalityProfiles(data, people);

  function evidence(title: string, description: string, ids: string[]) {
    onEvidence({
      id: `behavior-${ids[0] || title}`,
      family: "behavior",
      title,
      description,
      category: "Who does what?",
      section: "deep",
      value: "",
      label: "",
      participant_ids: [],
      facts: [],
      evidence_ids: ids,
      evidence_total: ids.length,
      method:
        "AI-classified messages. One count per message per category; nearby context is considered.",
      caveat:
        "Classification can miss context or sarcasm. These are expressions in messages, not personal traits.",
      visual_type: "none",
      visual: [],
      interpretation: true,
      source: "ai",
    });
  }

  if (!cards.length && !profiles.length) return null;

  return (
    <section id="who-does-what" className="behavior-section">
      <div className="behavior-heading">
        <div>
          <p className="eyebrow">The little things that make you, you</p>
          <h2>Who does what? 👀</h2>
          <p>
            The patterns you can spot at a glance. Tap any card for the full
            comparison and the messages behind it.
          </p>
        </div>
        <div className="behavior-coverage">
          <strong>{data.processed.toLocaleString()}</strong>
          <span>of {data.total.toLocaleString()} messages read</span>
          {data.version !== 1 && <small>Still reading · provisional</small>}
        </div>
      </div>

      {!!cards.length && (
        <div className="behavior-grid" aria-label="Message behavior comparisons">
          {cards.map((card) => {
            const leader = card.ranked[0];
            const max = Math.max(1, leader?.count || 0);
            return (
              <button
                type="button"
                key={card.key}
                className={`behavior-card behavior-tone-${card.tone}`}
                onClick={() => setActive(card)}
                aria-label={`Open details for ${card.title}`}
              >
                <span className="behavior-card-emoji" aria-hidden="true">
                  {card.emoji}
                </span>
                <span className="behavior-card-kicker">
                  {card.tied ? "A shared habit" : leader?.display_name}
                </span>
                <strong className="behavior-card-title">{card.title}</strong>
                <span className="behavior-card-stat">
                  {card.tied ? (
                    <>A tie at {leader?.count.toLocaleString()} messages</>
                  ) : (
                    <>
                      <b>{leader?.count.toLocaleString()}</b> tagged messages ·{" "}
                      {leader?.rate.toFixed(1)} per 100
                    </>
                  )}
                </span>
                <span className="behavior-mini-bars" aria-hidden="true">
                  {card.ranked.slice(0, 3).map((person) => (
                    <span className="behavior-mini-row" key={person.id}>
                      <i>{person.display_name}</i>
                      <span>
                        <i style={{ width: `${(person.count / max) * 100}%` }} />
                      </span>
                      <b>{person.count}</b>
                    </span>
                  ))}
                </span>
                <span className="behavior-card-open">
                  Open the receipts <ArrowUpRight size={13} />
                </span>
              </button>
            );
          })}
        </div>
      )}

      {!!profiles.length && (
        <div id="personalities" className="personality-section">
          <div className="personality-intro">
            <p className="eyebrow">🪞 Chat personality, by the receipts</p>
            <h3>Everyone has a signature way of showing up.</h3>
            <p>
              Playful communication-style tags built from tagged messages and
              explicit interests—not a psychological personality test.
            </p>
          </div>
          <div className="personality-grid">
            {profiles.map(({ person, tags, interests }, index) => (
              <article className="personality-card" key={person.id}>
                <div className="personality-avatar" aria-hidden="true">
                  {person.is_current_user
                    ? "🪞"
                    : ["🌸", "🌙", "🍊", "🦋"][index % 4]}
                </div>
                <p className="personality-name">
                  {person.display_name}
                  {person.is_current_user ? " · you" : ""}
                </p>
                {!!tags.length && (
                  <div className="personality-tags">
                    {tags.map((tag) => (
                      <button
                        key={tag.key}
                        onClick={() =>
                          setActive(
                            cards.find((card) => card.key === tag.key) || null,
                          )
                        }
                      >
                        <span>{tag.emoji}</span>
                        <span>
                          <strong>{tag.label}</strong>
                          <small>
                            {tag.count} message{tag.count === 1 ? "" : "s"} ·{" "}
                            {tag.rate.toFixed(1)} per 100
                          </small>
                        </span>
                      </button>
                    ))}
                  </div>
                )}
                {!!interests.length && (
                  <div className="personality-interests">
                    <span>Happy rabbit holes</span>
                    <div>
                      {interests.map((interest) => (
                        <button
                          key={interest.topic}
                          onClick={() =>
                            evidence(
                              `${person.display_name} · ${interest.topic}`,
                              "An explicitly expressed interest, classified by Gemini.",
                              interest.evidence_ids,
                            )
                          }
                        >
                          {interest.topic} · {interest.count} ↗
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </article>
            ))}
          </div>
        </div>
      )}

      <p className="behavior-footnote">
        Counts describe messages, not who loves more, who is to blame, or
        anyone’s actual sex drive. Empty topics are left out. {data.truncated ? `${data.truncated.toLocaleString()} long messages were shortened for this pass.` : ""}
      </p>
      {active && (
        <BehaviorDetails
          card={active}
          onClose={() => setActive(null)}
          onEvidence={evidence}
        />
      )}
    </section>
  );
}
