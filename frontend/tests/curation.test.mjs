import { test } from "node:test";
import assert from "node:assert/strict";
import { curate } from "../src/lib/curate.ts";
import {
  behaviorCards,
  personalityProfiles,
} from "../src/lib/behavior-presentation.ts";

test("routine moments stay out of highlights; categories and total cards are bounded", () => {
  const moments = Array.from({ length: 80 }, (_, i) => ({
    id: `m${i}`, family: `moment${i}`, title: `Finding ${i}`, source: "ai",
    moment_kind: `category${i % 8}`, display_score: i < 8 ? 3 : 8,
    score: 10, evidence_ids: [`source${i}`],
  }));
  const selected = curate(moments);
  assert.equal(selected.length, 24);
  assert.ok(selected.every(m => m.display_score >= 7));
  for (const kind of new Set(selected.map(m => m.moment_kind))) {
    assert.ok(selected.filter(m => m.moment_kind === kind).length <= 4);
  }
  assert.equal(moments.length, 80);
});

test("duplicate evidence and families do not fill the report", () => {
  const base = { source: "ai", moment_kind: "deep", display_score: 8, evidence_ids: ["a", "b"] };
  const selected = curate([
    { ...base, id: "a", title: "First", family: "reflection" },
    { ...base, id: "b", title: "Second", family: "another" },
    { ...base, id: "c", title: "Third", family: "reflection", evidence_ids: ["c", "d"] },
  ]);
  assert.equal(selected.length, 1);
});

const people = [
  { id: "alice", display_name: "Alice", is_current_user: true },
  { id: "sam", display_name: "Sam", is_current_user: false },
];

const behaviors = {
  processed: 200,
  total: 200,
  participant_messages: { alice: 100, sam: 100 },
  definitions: {
    affection: { title: "💗 Affection", description: "Warm words" },
    money: { title: "Money", description: "Money requests" },
  },
  categories: {
    affection: {
      alice: { count: 6, evidence_ids: ["a1"] },
      sam: { count: 2, evidence_ids: ["s1"] },
    },
    money: {},
  },
  interests: {
    travel: { alice: { count: 3, evidence_ids: ["a2"] } },
  },
};

test("behavior cards omit empty axes and retain visible comparison metrics", () => {
  const cards = behaviorCards(behaviors, people);
  assert.equal(cards.length, 1);
  assert.equal(cards[0].key, "affection");
  assert.equal(cards[0].title, "Affection");
  assert.equal(cards[0].ranked[0].display_name, "Alice");
  assert.equal(cards[0].ranked[0].rate, 6);
});

test("personality profiles use measured tags and explicit interests only", () => {
  const profiles = personalityProfiles(behaviors, people);
  assert.equal(profiles.length, 2);
  assert.equal(profiles[0].tags[0].label, "Heart on sleeve");
  assert.equal(profiles[0].interests[0].topic, "travel");
  assert.equal(profiles[1].interests.length, 0);
});
