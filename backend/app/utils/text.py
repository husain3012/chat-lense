def normalize_meta_text(value: str) -> str:
    """Repair reversible Meta UTF-8-as-Latin-1 mojibake; preserve valid Unicode."""
    try:
        repaired = value.encode("latin-1").decode("utf-8")
        return repaired
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
