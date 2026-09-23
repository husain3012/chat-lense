import type { ChatReport } from "@/lib/report-types";
import type { Person } from "@/lib/types";

export type BehaviorData = NonNullable<ChatReport["behaviors"]>;

export const behaviorLooks: Record<
  string,
  { emoji: string; tone: string; tag: string }
> = {
  friction: { emoji: "🌩️", tone: "storm", tag: "Debate mode" },
  swearing: { emoji: "🌶️", tone: "spice", tag: "Spicy vocabulary" },
  affection: { emoji: "💗", tone: "rose", tag: "Heart on sleeve" },
  desire: { emoji: "🔥", tone: "ember", tag: "Flirt energy" },
  money: { emoji: "💸", tone: "cash", tag: "Money logistics" },
  hunger: { emoji: "🍜", tone: "snack", tag: "Snack radar" },
  apology: { emoji: "🕊️", tone: "sky", tag: "Olive branch" },
  plans: { emoji: "🗓️", tone: "lilac", tag: "Plan maker" },
  gratitude: { emoji: "🌻", tone: "sun", tag: "Gratitude giver" },
  checking_in: { emoji: "🫶", tone: "mint", tag: "Check-in energy" },
};

export type BehaviorRank = Person & {
  count: number;
  rate: number;
  evidence_ids: string[];
};

export type BehaviorCardData = {
  key: string;
  title: string;
  description: string;
  emoji: string;
  tone: string;
  tag: string;
  total: number;
  tied: boolean;
  ranked: BehaviorRank[];
};

export function behaviorCards(
  data: BehaviorData,
  people: Person[],
): BehaviorCardData[] {
  return Object.entries(data.definitions)
    .map(([key, definition]) => {
      const counts = data.categories?.[key] || {};
      const ranked = people
        .map((person) => {
          const count = counts[person.id]?.count || 0;
          const messages = data.participant_messages?.[person.id] || 0;
          return {
            ...person,
            count,
            rate: messages ? (100 * count) / messages : 0,
            evidence_ids: counts[person.id]?.evidence_ids || [],
          };
        })
        .sort(
          (a, b) =>
            b.count - a.count ||
            b.rate - a.rate ||
            a.display_name.localeCompare(b.display_name),
        );
      const total = ranked.reduce((sum, person) => sum + person.count, 0);
      const look = behaviorLooks[key] || {
        emoji: "✨",
        tone: "lilac",
        tag: definition.title,
      };
      const title = behaviorLooks[key]
        ? definition.title.replace(/^\S+\s+/, "")
        : definition.title;
      return {
        key,
        ...definition,
        title,
        ...look,
        total,
        tied:
          ranked.length > 1 &&
          ranked[0].count > 0 &&
          ranked[0].count === ranked[1].count,
        ranked,
      };
    })
    .filter((card) => card.total > 0);
}

export type PersonalityTag = {
  key: string;
  label: string;
  emoji: string;
  count: number;
  rate: number;
};

export type PersonalityProfile = {
  person: Person;
  tags: PersonalityTag[];
  interests: { topic: string; count: number; evidence_ids: string[] }[];
};

export function personalityProfiles(
  data: BehaviorData,
  people: Person[],
): PersonalityProfile[] {
  return people
    .map((person) => {
      const messages = data.participant_messages?.[person.id] || 0;
      const tags = Object.entries(data.categories || {})
        .map(([key, counts]) => {
          const count = counts[person.id]?.count || 0;
          const look = behaviorLooks[key] || {
            emoji: "✨",
            tag: data.definitions[key]?.title || key,
          };
          return {
            key,
            label: look.tag,
            emoji: look.emoji,
            count,
            rate: messages ? (100 * count) / messages : 0,
          };
        })
        .filter((tag) => tag.count > 0)
        .sort(
          (a, b) =>
            b.rate * Math.log2(b.count + 1) -
              a.rate * Math.log2(a.count + 1) ||
            b.count - a.count,
        )
        .slice(0, 4);
      const interests = Object.entries(data.interests || {})
        .filter(([, counts]) => !!counts[person.id]?.count)
        .map(([topic, counts]) => ({
          topic,
          count: counts[person.id].count,
          evidence_ids: counts[person.id].evidence_ids,
        }))
        .sort((a, b) => b.count - a.count || a.topic.localeCompare(b.topic))
        .slice(0, 5);
      return { person, tags, interests };
    })
    .filter((profile) => profile.tags.length > 0 || profile.interests.length > 0);
}
