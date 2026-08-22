"""In-memory, per-visitor store used for the public ephemeral demo.

store.py switches to this backend automatically (see EPHEMERAL there) when
VERCEL or DASHBOARD_EPHEMERAL is set. Nothing here ever touches disk: each
visitor gets their own dataset keyed by a random id stamped into their
FastHTML session cookie (see app.py's assign_session Beforeware), a fresh
upload *replaces* that visitor's dataset rather than merging into it like
the local disk store does, and idle sessions are evicted so memory stays
bounded no matter how many people visit.
"""

import threading
import time
from contextvars import ContextVar
from datetime import datetime, timezone

from dashboard.data.normalize import normalize_all
from dashboard.data.schema import ITEMS_COLUMNS, RECEIPTS_COLUMNS, TENDERS_COLUMNS, empty_frame

MAX_SESSIONS = 50
SESSION_TTL_SECONDS = 2 * 60 * 60  # evict a visitor's data after 2h idle

_current_sid: ContextVar[str | None] = ContextVar("_current_sid", default=None)
_sessions: dict[str, dict] = {}
_lock = threading.Lock()


def set_session_id(sid: str) -> None:
    _current_sid.set(sid)


def _new_session() -> dict:
    return {
        "receipts": empty_frame(RECEIPTS_COLUMNS),
        "items": empty_frame(ITEMS_COLUMNS),
        "tenders": empty_frame(TENDERS_COLUMNS),
        "upload_history": [],
        "department_labels": {},
        "item_labels": {},
        "last_seen": time.monotonic(),
    }


def _evict_stale_locked() -> None:
    cutoff = time.monotonic() - SESSION_TTL_SECONDS
    for sid in [s for s, data in _sessions.items() if data["last_seen"] < cutoff]:
        del _sessions[sid]
    if len(_sessions) > MAX_SESSIONS:
        oldest_first = sorted(_sessions.items(), key=lambda kv: kv[1]["last_seen"])
        for sid, _ in oldest_first[: len(_sessions) - MAX_SESSIONS]:
            del _sessions[sid]


def _session() -> dict:
    sid = _current_sid.get()
    if sid is None:
        raise RuntimeError("No visitor session id set - is assign_session registered as Beforeware?")
    with _lock:
        _evict_stale_locked()
        data = _sessions.get(sid)
        if data is None:
            data = _sessions[sid] = _new_session()
        data["last_seen"] = time.monotonic()
        return data


def load_all():
    s = _session()
    return s["receipts"], s["items"], s["tenders"]


def merge_and_save(new_receipts, new_items, new_tenders) -> dict:
    """Replace this visitor's dataset with the freshly uploaded one.

    Unlike the disk store, a second upload in the same session discards the
    first rather than merging - there's no persisted history to reconcile
    against once the session ends, so "merge" would just mean "accumulate
    forever in memory" for no benefit.
    """
    s = _session()
    receipts_df, items_df, tenders_df = normalize_all(new_receipts, new_items, new_tenders)

    receipts_df = receipts_df.drop_duplicates(subset=["receipt_id"], keep="last")
    items_df = items_df.drop_duplicates(subset=["receipt_id", "line_no"], keep="last")
    tenders_df = tenders_df.drop_duplicates(
        subset=["receipt_id", "tender_type_name", "amount_tender"], keep="last"
    )

    s["receipts"], s["items"], s["tenders"] = receipts_df, items_df, tenders_df

    return {
        "receipts_added": len(receipts_df),
        "receipts_total": len(receipts_df),
        "items_added": len(items_df),
        "items_total": len(items_df),
    }


def record_upload(filename: str, format: str, receipts_added: int, items_added: int) -> None:
    s = _session()
    s["upload_history"].insert(
        0,
        {
            "id": len(s["upload_history"]) + 1,
            "filename": filename,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "format": format,
            "receipts_added": receipts_added,
            "items_added": items_added,
        },
    )


def get_upload_history() -> list[dict]:
    return list(_session()["upload_history"])


def get_department_labels() -> dict:
    return dict(_session()["department_labels"])


def set_department_label(dept_number: str, custom_label: str) -> None:
    _session()["department_labels"][dept_number] = custom_label


def get_item_labels() -> dict:
    return dict(_session()["item_labels"])


def set_item_label(item_number: str, custom_label: str) -> None:
    labels = _session()["item_labels"]
    if custom_label:
        labels[item_number] = custom_label
    else:
        labels.pop(item_number, None)
