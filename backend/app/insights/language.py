"""Literal recurring language, not inferred sentiment, topics, or inside jokes."""

from collections import defaultdict, Counter
from statistics import mean
from app.insights.candidates import pct
from app.insights.context import WORDS, LINK

STOP = set(
    "the a an and or but to of in on at for from with is are was were it its this that i you we they he she my your our their have has had be been not just can will would could should so if as do did all me us them".split()
)


def discover(c, out):
    phrases = defaultdict(list)
    exact = defaultdict(list)
    term_messages = defaultdict(list)
    for o in c.obs:
        if o.source.message_type != "text" or not o.words:
            continue
        words = [w.casefold() for w in WORDS.findall(LINK.sub("", o.text))]
        literal = " ".join(words)
        if 2 <= len(words) <= 8 and len(literal) <= 80:
            exact[literal].append(o)
        for term in set(words):
            if len(term) >= 4 and term not in STOP:
                term_messages[term].append(o)
        seen = set()
        for size in (2, 3):
            for j in range(len(words) - size + 1):
                segment = words[j : j + size]
                if sum(w not in STOP and len(w) >= 3 for w in segment) < 2:
                    continue
                phrase = " ".join(segment)
                if phrase not in seen:
                    phrases[phrase].append(o)
                    seen.add(phrase)
    recurring = [
        (len(v), phrase, v)
        for phrase, v in exact.items()
        if len(v) >= 3 and len({o.time.date() for o in v}) >= 3
    ]
    recurring.sort(key=lambda x: (-x[0], x[1]))
    if recurring:
        count, phrase, items = recurring[0]
        hours = Counter(o.time.hour for o in items)
        hour, hcount = hours.most_common(1)[0]
        clustered = pct(hcount, count) >= 60
        out.add(
            "recurring-ritual",
            "Recurring rituals",
            "Same words, familiar ritual",
            "Recurring short phrase",
            f"“{phrase}” appears as a complete message {count} times across {len({o.time.date() for o in items})} days."
            + (
                f" {pct(hcount, count):.0f}% land in the {hour:02}:00 hour. That is a remarkably punctual little ritual."
                if clustered
                else " A recurring line in this conversation’s vocabulary."
            ),
            str(count),
            "recorded repetitions",
            items,
            facts=[
                ("Occurrences", count, "messages"),
                ("Distinct days", len({o.time.date() for o in items}), "days"),
            ]
            + ([("Peak hour share", pct(hcount, count), "%")] if clustered else []),
            visual=[(f"{h:02}:00", v) for h, v in sorted(hours.items())],
            method="Exact phrase matching after case folding and word tokenization. A repeated phrase is not automatically an inside joke or a greeting.",
            score=6 if clustered else 4,
            multi=clustered,
        )
    candidates = sorted(
        [
            (len(v), p, v)
            for p, v in phrases.items()
            if len(v) >= 4 and len({o.time.date() for o in v}) >= 3
        ],
        key=lambda x: (-x[0], -len(x[1]), x[1]),
    )
    chosen = []
    chosen_populations = []
    for count, phrase, items in candidates:
        if any(phrase in p or p in phrase for p in chosen):
            continue
        if recurring and phrase in recurring[0][1]:
            continue
        population = {o.id for o in items}
        # Overlapping n-grams from the same messages are one discovery.
        if any(
            len(population & old) / min(len(population), len(old)) >= 0.8
            for old in chosen_populations
        ):
            continue
        chosen.append(phrase)
        chosen_populations.append(population)
        participant_count = len({o.sender_id for o in items})
        out.add(
            "phrase-" + str(len(chosen)),
            "Recurring language",
            f"“{phrase}” has entered the chat",
            "Repeated phrase: " + phrase,
            f"This phrase turns up in {count} messages from {participant_count} {'participant' if participant_count == 1 else 'participants'}, spread across {len({o.time.date() for o in items})} days.",
            str(count),
            "messages with this phrase",
            items,
            facts=[
                ("Messages", count, "messages"),
                ("Participants", len({o.sender_id for o in items}), "people"),
            ],
            visual=list(Counter(o.time.strftime("%Y-%m") for o in items).items()),
            method="Literal two/three-word sequences; counted once per message. This is recurring language, not a semantic topic or proof of an inside joke.",
            section="topics",
            score=3,
        )
        if len(chosen) >= 3:
            break
    # Vocabulary-conditioned style contrasts use repeated support on both sides.
    changes = []
    totals = {
        pid: (len(c.text(pid)), sum(o.length for o in c.text(pid))) for pid in c.own
    }
    for term, items in term_messages.items():
        if len(items) < 8 or len({o.time.date() for o in items}) < 3:
            continue
        by_person = defaultdict(list)
        for o in items:
            by_person[o.sender_id].append(o)
        for pid, own in by_person.items():
            if len(own) < 5:
                continue
            total_count, total_length = totals[pid]
            remaining = total_count - len(own)
            if remaining < 10:
                continue
            a = mean(o.length for o in own)
            b = (total_length - sum(o.length for o in own)) / remaining
            if b and a / b >= 1.8:
                changes.append((a / b, term, pid, own, a, b))
    if changes:
        ratio, term, pid, items, a, b = max(changes, key=lambda x: x[0])
        out.add(
            "word-length-context",
            "Message style",
            "A word that unlocks essay mode",
            "Message length around a recurring word",
            f"{c.name(pid)}’s texts containing “{term}” average {a:.0f} characters, versus {b:.0f} for their other texts: {ratio:.1f}× as long.",
            f"{ratio:.1f}×",
            "length around this word",
            items,
            facts=[("With word", a, "characters"), ("Without word", b, "characters")],
            visual=[("Contains “" + term + "”", a), ("Other texts", b)],
            method="Literal word-conditioned comparison with at least five matching and ten other texts. Correlation only: longer texts have more chances to contain any word.",
            score=5,
            pids=[pid],
            caveat="A lexical association, not a claim about what causes longer messages.",
        )
