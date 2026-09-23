import { test } from "node:test";
import assert from "node:assert/strict";
import { curate } from "../src/lib/curate.ts";

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
