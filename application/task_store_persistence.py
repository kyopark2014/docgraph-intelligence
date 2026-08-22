"""Persist global + per-user task DBs on local disk only.

Global ``tasks.db`` holds ``login_events`` (and legacy tasks/messages for migrate).
Per-user working DB: ``application/data/users/{user}.db``.
Per-user durable copy: ``.session_storage/{user}/{user}.db``.

No S3 download/upload and no remote mount sync.
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import threading
from typing import Iterable

from application import app_data_backend as backend

logger = logging.getLogger("task_store_persistence")

_PERSIST_DEBOUNCE_SECONDS = 20.0

_persist_lock = threading.Lock()
_persist_timer: threading.Timer | None = None
_global_dirty = False
_dirty_users: set[str] = set()


def persistence_enabled() -> bool:
    """Local durable mirror under session_storage is always available."""
    return True


def working_db_path() -> str:
    """Global/legacy working DB path."""
    return backend.working_tasks_db_path()


def persistent_db_path() -> str:
    """Local working DB path (no remote durable store)."""
    return working_db_path()


def _user_segment(user_id: str) -> str:
    from application.utils import sanitize_user_path_segment

    segment = sanitize_user_path_segment(user_id)
    if not segment:
        raise ValueError(f"Invalid user_id for DB path: {user_id!r}")
    return segment


def working_user_db_path(user_id: str) -> str:
    return backend.working_user_db_path(_user_segment(user_id))


def durable_user_db_path(user_id: str) -> str:
    """Canonical durable path under SESSION_STORAGE_DIR/{user}/{user}.db."""
    from application.utils import get_user_db_path

    return get_user_db_path(user_id)


def persistent_user_db_path(user_id: str) -> str:
    return durable_user_db_path(user_id)


def _db_ready(path: str) -> bool:
    return os.path.isfile(path) and os.path.getsize(path) > 0


def _copy_db_files(source: str, destination: str) -> None:
    """Copy DB bytes only (no metadata/xattrs)."""
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    shutil.copy(source, destination)
    for suffix in ("-wal", "-shm"):
        src = source + suffix
        dst = destination + suffix
        if os.path.isfile(src):
            shutil.copy(src, dst)
        elif os.path.isfile(dst):
            os.remove(dst)


def _checkpoint_sqlite(db_path: str) -> None:
    if not os.path.isfile(db_path):
        return
    conn = sqlite3.connect(db_path, timeout=5)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()
    finally:
        conn.close()


def _remove_db_files(path: str) -> None:
    for candidate in (path, path + "-wal", path + "-shm"):
        try:
            if os.path.isfile(candidate):
                os.remove(candidate)
        except OSError as exc:
            logger.warning("Could not remove %s: %s", candidate, exc)


def restore_tasks_db() -> None:
    """Local mode: no remote restore; working global DB is used as-is."""
    logger.info(
        "Task DB local-only mode; working path=%s",
        working_db_path(),
    )


def restore_user_db(user_id: str) -> bool:
    """Copy local durable DB into the working path if available."""
    working = working_user_db_path(user_id)
    durable = durable_user_db_path(user_id)
    if not _db_ready(durable):
        return False
    os.makedirs(os.path.dirname(working), exist_ok=True)
    _remove_db_files(working)
    _copy_db_files(durable, working)
    logger.info("Restored user DB from local durable: %s -> %s", durable, working)
    return True


def _persist_user(user_id: str) -> None:
    working = working_user_db_path(user_id)
    if not _db_ready(working):
        logger.warning("Working user DB missing, skip persist: %s", working)
        return
    try:
        _checkpoint_sqlite(working)
        _copy_db_files(working, durable_user_db_path(user_id))
        logger.info(
            "Persisted user DB locally: %s -> %s",
            working,
            durable_user_db_path(user_id),
        )
    except Exception:
        logger.exception("Failed to persist user DB for %s", user_id)


def persist_tasks_db(*, force: bool = False, user_id: str | None = None) -> None:
    """Flush working user SQLite DB(s) to local durable session_storage.

    Global DB is not mirrored remotely in local mode.
    """
    global _global_dirty

    with _persist_lock:
        users: Iterable[str]
        if user_id is not None:
            users = (user_id,)
        else:
            users = list(_dirty_users)

        _global_dirty = False

        for uid in users:
            _persist_user(uid)
            _dirty_users.discard(uid)


def _start_persist_timer_locked() -> None:
    """Caller must hold ``_persist_lock``."""
    global _persist_timer

    def _run() -> None:
        persist_tasks_db(force=True)

    if _persist_timer is not None:
        _persist_timer.cancel()
    _persist_timer = threading.Timer(_PERSIST_DEBOUNCE_SECONDS, _run)
    _persist_timer.daemon = True
    _persist_timer.start()


def schedule_persist(user_id: str | None = None) -> None:
    """Debounced persist after mutations. ``user_id=None`` is a no-op in local mode."""
    with _persist_lock:
        if user_id is None:
            return
        _dirty_users.add(user_id)
        _start_persist_timer_locked()


def flush_persist(user_id: str | None = None) -> None:
    """Cancel pending debounce and persist immediately."""
    global _persist_timer

    with _persist_lock:
        if _persist_timer is not None:
            _persist_timer.cancel()
            _persist_timer = None

    if user_id is not None:
        persist_tasks_db(force=True, user_id=user_id)
        with _persist_lock:
            if _dirty_users:
                _start_persist_timer_locked()
        return

    persist_tasks_db(force=True)
