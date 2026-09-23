"""Reusable measured facts: no generated claims, no probabilistic inference."""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timezone
from statistics import mean
from zoneinfo import ZoneInfo
from app.analytics.sessions import calculate as detect_sessions
from app.analytics.interactions import resolver

WORDS = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)
LINK = re.compile(r"https?://[^\s]+", re.I)
EMOJI = re.compile("[\U0001f300-\U0001faff\u2600-\u27bf]")
MEDIA = {"image", "video", "audio", "file", "sticker"}


@dataclass
class Observation:
    source: object
    time: object
    words: list[str]
    length: int
    questions: bool
    links: int
    emoji: bool

    @property
    def id(self):
        return self.source.id

    @property
    def sender_id(self):
        return self.source.sender_id

    @property
    def text(self):
        return self.source.text or ""


class Context:
    def __init__(
        self, messages, people, kind, metadata, gap_hours=4, timezone_name="UTC"
    ):
        self.people = people
        self.names = {p.id: p.display_name for p in people}
        self.kind, self.metadata, self.gap = kind, metadata, gap_hours * 3600
        self.timezone_name = timezone_name
        zone = ZoneInfo(timezone_name)
        self.messages = sorted(messages, key=lambda m: (m.timestamp, m.sequence, m.id))
        self.obs = []
        self.own = defaultdict(list)
        self.days, self.hours, self.weekdays = (
            defaultdict(list),
            defaultdict(list),
            defaultdict(list),
        )
        self.months = defaultdict(list)
        self.by_id = {}
        self.by_external = {}
        for m in self.messages:
            if not m.sender_id or m.message_type == "system":
                continue
            utc = (
                m.timestamp.replace(tzinfo=timezone.utc)
                if m.timestamp.tzinfo is None
                else m.timestamp
            )
            text = m.text or ""
            # Media placeholders/deletion notices must not masquerade as prose.
            prose = text if m.message_type == "text" else ""
            o = Observation(
                m,
                utc.astimezone(zone),
                WORDS.findall(prose),
                len(prose),
                "?" in prose or "؟" in prose or "？" in prose,
                len(LINK.findall(prose)),
                bool(EMOJI.search(prose)),
            )
            self.obs.append(o)
            self.own[m.sender_id].append(o)
            self.days[o.time.date()].append(o)
            self.hours[o.time.hour].append(o)
            self.weekdays[o.time.weekday()].append(o)
            self.months[o.time.strftime("%Y-%m")].append(o)
            self.by_id[m.id] = o
            if m.platform_message_id:
                self.by_external[m.platform_message_id] = o
        self.sessions = []
        for s in detect_sessions(self.messages, self.gap):
            own = [self.by_id[m.id] for m in s if m.id in self.by_id]
            if own:
                self.sessions.append(own)
        self.starts = Counter(s[0].sender_id for s in self.sessions)
        self.ends = Counter(s[-1].sender_id for s in self.sessions)
        self.revivals = []
        for a, b in zip(self.obs, self.obs[1:]):
            if (b.time.timestamp() - a.time.timestamp()) >= max(8 * 3600, self.gap):
                self.revivals.append((a, b))
        self.runs = []
        for o in self.obs:
            if (
                not self.runs
                or self.runs[-1][-1].sender_id != o.sender_id
                or (o.time.timestamp() - self.runs[-1][-1].time.timestamp()) > self.gap
            ):
                self.runs.append([])
            self.runs[-1].append(o)
        self.bursts = [
            r
            for r in self.runs
            if len(r) >= 3 and (r[-1].time.timestamp() - r[0].time.timestamp()) <= 120
        ]
        self.responses = []
        self.explicit = []
        previous = None
        for o in self.obs:
            parent = self.by_external.get(o.source.reply_to_id)
            if parent and parent.sender_id != o.sender_id and parent.time <= o.time:
                self.explicit.append((parent, o))
            target = previous if kind == "direct" else parent
            if target and target.sender_id != o.sender_id:
                seconds = o.time.timestamp() - target.time.timestamp()
                if 0 <= seconds <= self.gap:
                    self.responses.append((target, o, seconds))
            previous = o
        aliases = resolver(people)
        self.reaction_events = []
        self.reaction_total = 0
        self.reaction_received = Counter()
        self.unknown_reactors = 0
        for o in self.obs:
            for r in o.source.reactions:
                count = max(0, int(r.get("count", 1)))
                self.reaction_total += count
                self.reaction_received[o.sender_id] += count
                known = 0
                for actor in r.get("actors", []):
                    pid = aliases.get(str(actor))
                    if pid:
                        self.reaction_events.append((pid, o, r.get("emoji", "?")))
                        known += 1
                self.unknown_reactors += max(0, count - known)

    def name(self, pid):
        return self.names.get(pid, "Unknown participant")

    def text(self, pid):
        return [o for o in self.own[pid] if o.source.message_type == "text"]

    def late(self, o):
        return o.time.hour >= 23 or o.time.hour < 5

    def metric_by_person(self, fn):
        return {p.id: fn(self.own[p.id]) for p in self.people if self.own[p.id]}

    def evidence(self, observations):
        return list(dict.fromkeys(o.id for o in observations))[:12]

    def average(self, items):
        return (
            mean([o.length for o in items if o.source.message_type == "text"])
            if any(o.source.message_type == "text" for o in items)
            else 0
        )

    def peak_window(self, minutes=10):
        start = 0
        best_start, best_end = 0, 0
        for end, o in enumerate(self.obs):
            while o.time.timestamp() - self.obs[start].time.timestamp() > minutes * 60:
                start += 1
            if end + 1 - start > best_end - best_start:
                best_start, best_end = start, end + 1
        return self.obs[best_start:best_end]
