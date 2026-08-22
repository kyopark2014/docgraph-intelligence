"""Local application data paths (working SQLite under application/data).

Remote backends (S3 API / S3 Files mount) are not used — local mode only.
"""

from __future__ import annotations

import os

_APPLICATION_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_WORKING_DIR = os.path.join(_APPLICATION_DIR, "data")


def working_dir() -> str:
    custom = (os.environ.get("APP_DATA_DIR") or "").strip()
    if custom:
        return custom
    return _DEFAULT_WORKING_DIR


def backend_mode() -> str:
    """Always local for this project."""
    return "local"


def working_tasks_db_path() -> str:
    """Global/legacy DB working path (login_events + migrate source)."""
    custom = (os.environ.get("TASK_DB_WORKING_PATH") or "").strip()
    if custom:
        return custom
    return os.path.join(working_dir(), "tasks.db")


def working_user_db_path(user_segment: str) -> str:
    """Per-user tasks/messages working DB under data/users/{segment}.db."""
    segment = (user_segment or "").strip()
    if not segment or "/" in segment or "\\" in segment or ".." in segment:
        raise ValueError(f"Invalid user DB segment: {user_segment!r}")
    return os.path.join(working_dir(), "users", f"{segment}.db")
