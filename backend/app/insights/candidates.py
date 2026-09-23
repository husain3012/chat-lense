"""Candidate creation, evidence selection, conservative winner handling and ranking."""

import math
import hashlib
from app.schemas.report import Insight, Fact, VisualPoint


def fmt(value):
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"


def pct(n, d):
    return n / d * 100 if d else 0


def span(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.0f}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def winner(values, minimum=1):
    ordered = sorted(values.items(), key=lambda x: (-x[1], x[0]))
    if not ordered or ordered[0][1] < minimum:
        return None
    if len(ordered) > 1 and abs(ordered[0][1] - ordered[1][1]) < 1e-9:
        return None
    return ordered[0]


class Candidates:
    def __init__(self, context, tone):
        self.c = context
        self.tone = tone
        self.items = []
        self.populations = {}

    def add(
        self,
        key,
        category,
        fun,
        plain,
        description,
        value,
        label,
        observations,
        *,
        facts=(),
        visual=(),
        method,
        score=1,
        section="deep",
        pids=(),
        caveat=None,
        multi=False,
    ):
        observations = list(observations)
        if key in ("pair-reaction", "reaction-magnet", "award-reactions-given"):
            digest = hashlib.sha256(
                "|".join(sorted(o.id for o in observations)).encode()
            ).hexdigest()
            self.populations[key] = (digest, facts[0][1] if facts else None)
        title = (
            plain if self.tone == "analytical" else fun if self.tone == "fun" else plain
        )
        if self.tone == "analytical":
            description = (
                "; ".join(f"{k}: {fmt(v)} {u}" for k, v, u in facts)
                + ". "
                + method.split(". ")[0]
                + "."
            )
        # Magnitude + support, rather than a fabricated statistical confidence score.
        interest = round(score + min(3, math.log10(max(1, len(observations)))), 3)
        self.items.append(
            Insight(
                id=key,
                family=key,
                category=category,
                section=section,
                title=title,
                description=description,
                value=str(value),
                label=label,
                participant_ids=list(pids),
                facts=[Fact(label=k, value=v, unit=u) for k, v, u in facts],
                evidence_ids=self.c.evidence(observations),
                evidence_total=len(observations),
                method=method,
                caveat=caveat,
                visual_type="pair"
                if section == "pairs"
                else "trend"
                if category == "Turning points"
                else "bars",
                visual=[VisualPoint(label=k, value=v) for k, v in visual],
                score=interest,
                interpretation=multi,
            )
        )

    def sorted(self):
        # A finding has one home. Stable family identity prevents cross-section paraphrases.
        unique = {}
        for i in self.items:
            if i.family not in unique or i.score > unique[i.family].score:
                unique[i.family] = i
        # When one pair accounts for every reaction, three perspectives on the
        # exact same event population are one finding, not three discoveries.
        priority = {
            "pair-reaction": 3,
            "reaction-magnet": 2,
            "award-reactions-given": 1,
        }
        retained = {}
        for key, signature in self.populations.items():
            previous = retained.get(signature)
            if previous is None or priority[key] > priority[previous]:
                if previous:
                    unique.pop(previous, None)
                retained[signature] = key
            else:
                unique.pop(key, None)
        items = sorted(unique.values(), key=lambda i: (-i.score, i.id))
        top = []
        categories = {}
        eligible = [i for i in items if i.section == "deep"]
        for i in eligible:
            if len(top) >= 7:
                break
            if categories.get(i.category, 0) >= 2:
                continue
            top.append(i)
            categories[i.category] = categories.get(i.category, 0) + 1
        for i in top:
            i.section = "top"
        limit = 50 if self.c.kind == "group" else 30
        # Keep the rich structural sections even if many candidates compete for space.
        structural = [
            i
            for i in items
            if i.section in ("micro", "participants", "superlatives", "pairs", "top")
        ]
        remaining = [i for i in items if i not in structural]
        return sorted(
            structural + remaining[: max(0, limit - len(structural))],
            key=lambda i: (-i.score, i.id),
        )
