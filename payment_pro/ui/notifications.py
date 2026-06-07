from datetime import datetime

_store: list[dict] = []

ICONS = {"success": "✓", "error": "✗", "info": "i", "warning": "!"}
COLORS = {"success": "#10B981", "error": "#EF4444", "info": "#3B82F6", "warning": "#F59E0B"}


def add(message: str, kind: str = "info"):
    _store.append({
        "message": message,
        "kind": kind,
        "time": datetime.now().strftime("%H:%M"),
    })
    if len(_store) > 30:
        _store.pop(0)


def get_all() -> list[dict]:
    return list(reversed(_store))


def clear():
    _store.clear()
