"""Private, bounded exports from saved findings. No generation or external assets."""

import html
import re
import subprocess
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field


class WrapRequest(BaseModel):
    finding_ids: list[str] = Field(default_factory=list, max_length=50)
    aliases: bool = True
    include_verdict: bool = False
    title: str = Field(default="Our chat, wrapped.", min_length=1, max_length=80)
    palette: Literal["peach", "lilac", "mint"] = "peach"
    seconds_per_slide: int = Field(default=6, ge=4, le=10)


PALETTES = {
    "peach": ["#ffe1ce", "#fff2c6", "#e4ddff", "#d8eee2"],
    "lilac": ["#e4ddff", "#f7dce8", "#dde9ff", "#fff2c6"],
    "mint": ["#d8eee2", "#fff2c6", "#dcecff", "#ffe1ce"],
}


def slides(report, people, request):
    names = [(p.display_name, f"Person {i + 1}") for i, p in enumerate(people)]

    def clean(value):
        text = str(value or "")
        if request.aliases:
            # Replace once, so short names cannot corrupt words or generated aliases.
            mapping = {name.casefold(): alias for name, alias in names if name}
            patterns = []
            for name in sorted(mapping, key=len, reverse=True):
                pattern = re.escape(name)
                if not any("\u3400" <= c <= "\u9fff" for c in name):
                    pattern = r"(?<!\w)" + pattern + r"(?!\w)"
                patterns.append(pattern)
            if patterns:
                text = re.sub(
                    "|".join(patterns),
                    lambda m: mapping[m.group().casefold()],
                    text,
                    flags=re.I,
                )
        return text

    snapshot = report.get("snapshot", {})
    findings = {
        f["id"]: f
        for f in [
            *report.get("insights", []),
            *(report.get("synthesis") or {}).get("insights", []),
        ]
    }
    result = [
        {
            "label": "YOUR CHAT WRAP",
            "emoji": "💌",
            "title": clean(request.title),
            "body": f"{snapshot.get('messages', 0):,} messages. {snapshot.get('active_days', 0):,} days with a hello. One story worth keeping.",
            "note": " + ".join(
                alias if request.aliases else name for name, alias in names[:6]
            ),
        }
    ]
    for fid in dict.fromkeys(request.finding_ids):
        if fid not in findings:
            raise ValueError(
                "A selected finding is no longer available in this conversation. Refresh the preview."
            )
        f = findings[fid]
        result.append(
            {
                "label": clean(f.get("category", "A LITTLE DISCOVERY"))[:80],
                "emoji": {
                    "sweet": "🫶",
                    "funny": "😂",
                    "romance": "💞",
                    "repair": "🌤️",
                    "tension": "🌧️",
                    "ideas": "💡",
                    "missing": "🥹",
                }.get(f.get("moment_kind"), "✨"),
                "title": clean(f["title"]),
                "body": clean(f["description"]),
                "metric": clean(f.get("value", "")) if f.get("source") != "ai" else "",
                "metric_label": clean(f.get("label", "")),
                "note": "AI interpretation · based on your chat"
                if f.get("source") == "ai"
                else "Counted from your messages",
                "caveat": clean(f.get("caveat", "")),
            }
        )
    if request.include_verdict and report.get("verdict"):
        verdict = report["verdict"]
        result.append(
            {
                "label": "THE BIGGER PICTURE",
                "emoji": "🌱",
                "title": "A little perspective.",
                "body": clean(verdict["summary"]),
                "caveat": clean(verdict.get("suggestion", "")),
                "note": "AI interpretation · a perspective, not a diagnosis",
            }
        )
    result.append(
        {
            "label": "TO BE CONTINUED",
            "emoji": "🪩",
            "title": "Same people.\nA whole new perspective.",
            "body": "The best part? The story is still being written.",
            "note": "Made with ChatLens · your conversations, rediscovered",
        }
    )
    # Continue long readings on additional pages rather than dropping text or
    # reducing type to an unreadable size. Works with or without word spaces.
    expanded = []
    for slide in result:
        remaining = slide["body"]
        chunks = []
        while len(remaining) > 650:
            boundary = remaining.rfind(" ", 400, 650)
            boundary = boundary if boundary > 0 else 650
            chunks.append(remaining[:boundary])
            remaining = remaining[boundary:].lstrip()
        chunks.append(remaining)
        for index, body in enumerate(chunks):
            expanded.append(
                {
                    **slide,
                    "body": body,
                    "label": slide["label"]
                    + (f" · {index + 1}/{len(chunks)}" if len(chunks) > 1 else ""),
                    "metric": slide.get("metric", "") if index == 0 else "",
                    "caveat": slide.get("caveat", "")
                    if index == len(chunks) - 1
                    else "",
                }
            )
    result = expanded
    for i, slide in enumerate(result):
        slide.update(
            color=PALETTES[request.palette][i % 4], number=i + 1, total=len(result)
        )
    return result


CSS = """
*{box-sizing:border-box}html,body{margin:0;background:#fff;font-family:'Noto Sans',Arial,sans-serif;color:#30283c}
.slide{width:720px;height:1280px;position:relative;overflow:hidden;padding:100px 62px 110px;break-after:page;display:flex;flex-direction:column;justify-content:center}
.slide:last-child{break-after:auto}.blob{position:absolute;width:430px;height:430px;border:2px solid #30283c14;border-radius:47% 53% 65% 35%;right:-160px;top:-80px;transform:rotate(30deg)}
.blob.two{right:auto;left:-250px;top:auto;bottom:30px;width:580px;height:580px}
.brand{position:absolute;top:64px;left:62px;font-size:22px;font-weight:700;letter-spacing:-.6px}.number{position:absolute;right:62px;top:70px;font-size:16px;letter-spacing:3px}
.content{position:relative;max-height:970px;overflow-wrap:anywhere}.emoji{font-family:'Noto Color Emoji',sans-serif;font-size:94px;margin-bottom:32px}
.label{font-size:17px;font-weight:800;letter-spacing:2px;text-transform:uppercase;margin-bottom:20px}
h1{font-size:62px;line-height:1.08;letter-spacing:-2.5px;margin:0 0 28px;font-weight:850;white-space:pre-line}
.body{font-size:27px;line-height:1.55;white-space:pre-line;margin:0}.caveat{font-size:20px;line-height:1.45;margin:24px 0 0;opacity:.85}
.note{font-size:17px;line-height:1.4;margin-top:30px;border-top:1px solid #30283c33;padding-top:20px}
.metric{font-size:84px;font-weight:900;letter-spacing:-3px;line-height:1.1;margin:0 0 8px}.metric-label{font-size:18px;margin:0 0 28px}
.footer{position:absolute;bottom:62px;left:62px;right:62px;display:flex;justify-content:space-between;font-size:16px}.dots{letter-spacing:5px}
@page{size:720px 1280px;margin:0} @media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def document(items):
    def esc(value):
        return html.escape(str(value))

    pages = []
    for s in items:
        # All fields are escaped, including source conversation text. No uploaded HTML executes.
        pages.append(f"""<section class="slide" style="background:{esc(s["color"])}">
        <div class="blob"></div><div class="blob two"></div><div class="brand">✳ ChatLens</div>
        <div class="number">{s["number"]:02d} / {s["total"]:02d}</div><div class="content">
        <div class="emoji">{esc(s["emoji"])}</div><div class="label">{esc(s["label"])}</div>
        <h1>{esc(s["title"])}</h1>{'<div class="metric">' + esc(s.get("metric", "")) + '</div><div class="metric-label">' + esc(s.get("metric_label", "")) + "</div>" if s.get("metric") else ""}<p class="body">{esc(s["body"])}</p>
        <p class="caveat">{esc(s.get("caveat", ""))}</p><div class="note">{esc(s["note"])}</div></div>
        <div class="footer"><span>a little closer, a little clearer.</span><span class="dots">✦ ✧ ✦</span></div></section>""")
    return (
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        + CSS
        + "</style></head><body>"
        + "".join(pages)
        + "</body></html>"
    )


def render(items, format, folder: Path, seconds):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--disable-dev-shm-usage"])
        try:
            context = browser.new_context(
                viewport={"width": 720, "height": 1280}, java_script_enabled=False
            )
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(document(items))
            # Fit long multilingual findings without truncating their meaning.
            for card in page.locator(".content").all():
                card.evaluate(
                    """el => { let scale=1; while(el.scrollHeight>940 && scale>.64){scale-=.04; el.querySelector('h1').style.fontSize=62*scale+'px'; el.querySelector('.body').style.fontSize=27*scale+'px'; el.querySelector('.emoji').style.fontSize=94*scale+'px'; const metric=el.querySelector('.metric');if(metric)metric.style.fontSize=84*scale+'px';} }"""
                )
                if card.evaluate("el => el.scrollHeight") > 970:
                    raise ValueError(
                        "A selected finding is too long for a readable share slide. Choose a shorter finding."
                    )
            if format == "pdf":
                page.pdf(
                    path=str(folder / "chatlens-wrap.pdf"),
                    print_background=True,
                    prefer_css_page_size=True,
                )
            else:
                for i, card in enumerate(page.locator(".slide").all()):
                    card.screenshot(path=str(folder / f"slide-{i:02d}.png"))
        finally:
            browser.close()
    if format == "mp4":
        parts = []
        for i in range(len(items)):
            part = folder / f"part-{i:02d}.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(folder / f"slide-{i:02d}.png"),
                    "-vf",
                    f"zoompan=z='min(zoom+0.00018,1.025)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={seconds * 24}:s=720x1280:fps=24,fade=t=in:d=0.25,fade=t=out:st={seconds - 0.25}:d=0.25,format=yuv420p",
                    "-t",
                    str(seconds),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-threads",
                    "2",
                    "-crf",
                    "22",
                    str(part),
                ],
                check=True,
                timeout=45,
                capture_output=True,
            )
            parts.append(f"file '{part.name}'")
        (folder / "parts.txt").write_text("\n".join(parts))
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "1",
                "-i",
                str(folder / "parts.txt"),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(folder / "chatlens-wrap.mp4"),
            ],
            check=True,
            timeout=30,
            capture_output=True,
        )
    return folder / f"chatlens-wrap.{format}"
