from app.parsers.whatsapp import WhatsAppParser
from app.parsers.telegram import TelegramParser
from app.parsers.instagram import InstagramParser
from app.parsers.imessage import IMessageParser

PARSERS = {
    "whatsapp": WhatsAppParser,
    "telegram": TelegramParser,
    "instagram": InstagramParser,
    "imessage": IMessageParser,
}


def detect(path):
    scores = {}
    for name, parser in PARSERS.items():
        try:
            scores[name] = parser.detect(path)
        except (ValueError, OSError, UnicodeError):
            scores[name] = 0.0
    platform = max(scores, key=scores.get)
    return {
        "platform": platform if scores[platform] else None,
        "confidence": scores[platform],
        "scores": scores,
    }


def parse(path, platform, date_order="auto"):
    if platform not in PARSERS:
        raise ValueError("Select a supported platform")
    parser = (
        WhatsAppParser(date_order) if platform == "whatsapp" else PARSERS[platform]()
    )
    issues = parser.validate(path)
    if issues:
        raise ValueError("; ".join(issues))
    conversations = parser.parse(path)
    if not conversations or not any(c.message_count for c in conversations):
        raise ValueError("No supported messages found in this export")
    return conversations
