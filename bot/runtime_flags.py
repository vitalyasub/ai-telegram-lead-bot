from __future__ import annotations

from pathlib import Path

FLAG_FILE = Path("leads_enabled.flag")


def is_leads_enabled(default: bool = True) -> bool:
    if FLAG_FILE.exists():
        return FLAG_FILE.read_text(encoding="utf-8").strip() == "1"
    return default


def set_leads_enabled(enabled: bool) -> None:
    FLAG_FILE.write_text("1" if enabled else "0", encoding="utf-8")