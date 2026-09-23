import type { Finding } from "@/lib/report-types";
import { momentStyles, sticker } from "./moment-style";

export function createCard(finding: Finding, title: string) {
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 1200;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Image export is unavailable in this browser.");
  const gradient = ctx.createLinearGradient(0, 0, 1200, 1200);
  gradient.addColorStop(0, "#fff7ed");
  gradient.addColorStop(1, "#f3dfec");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 1200, 1200);
  ctx.font = "52px sans-serif";
  ctx.fillText(sticker(finding.category), 1040, 104);
  ctx.fillStyle = "#a15377";
  ctx.font = "600 22px Arial";
  ctx.fillText("CHATLENS  /  ONE FOR THE SCRAPBOOK", 80, 95);
  function wrapped(
    text: string,
    x: number,
    y: number,
    width: number,
    lineHeight: number,
    maxLines: number,
  ) {
    let line = "";
    let lines = 0;
    for (const word of text.split(/\s+/)) {
      if (ctx!.measureText(line + word).width > width && line) {
        ctx!.fillText(line, x, y);
        y += lineHeight;
        line = "";
        lines++;
        if (lines >= maxLines) {
          ctx!.fillText("…", x, y);
          return y + lineHeight;
        }
      }
      line += word + " ";
    }
    ctx!.fillText(line, x, y);
    return y + lineHeight;
  }
  ctx.fillStyle = "#49354e";
  ctx.font = "600 58px Arial";
  let y = wrapped(finding.title, 80, 205, 1040, 70, 3);
  ctx.fillStyle = "#9c496b";
  ctx.font = "700 132px Arial";
  ctx.fillText(
    finding.source === "ai"
      ? momentStyles[finding.moment_kind || "connection"]?.emoji || "💬"
      : finding.value.slice(0, 18),
    80,
    y + 145,
    1040,
  );
  y += 205;
  ctx.fillStyle = "#835875";
  ctx.font = "28px Arial";
  y =
    wrapped(
      finding.source === "ai"
        ? momentStyles[finding.moment_kind || "connection"]?.label ||
            "A little moment"
        : finding.label,
      80,
      y,
      1040,
      38,
      2,
    ) + 45;
  ctx.fillStyle = "#49354e";
  ctx.font = "32px Arial";
  wrapped(finding.description, 80, y, 1040, 46, 5);
  ctx.fillStyle = "#835875";
  ctx.font = "22px Arial";
  ctx.fillText(
    finding.source === "ai"
      ? "Gemini interpretation · sampled evidence"
      : "Measured from exported messages",
    80,
    1050,
  );
  ctx.font = "18px Arial";
  ctx.fillText(title.slice(0, 95), 80, 1100);
  ctx.fillText(
    "Only this finding is included. Review before sharing.",
    80,
    1140,
  );
  return canvas.toDataURL("image/png");
}
