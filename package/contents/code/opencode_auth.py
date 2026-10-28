"""Credentials OpenCode keeps for its provider integrations (Z.ai GLM
Coding Plan, OpenCode Go, ...).

Since v2 OpenCode stores them in opencode.db and a re-login no longer
rewrites auth.json, so the file entry goes stale while the CLI itself
keeps working: the database entry wins where both exist, and the file
alone still covers a v1 install. Shared by fetch_usage.py and
token_stats.py.
"""

import json
import os
import sqlite3
import urllib.request


def _base():
    return os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share")


def load():
    """Return {integration: {key, ...}}, database values over the file's."""
    auth = {}
    try:
        with open(os.path.join(_base(), "opencode", "auth.json")) as f:
            loaded = json.load(f)
        # Values can be any JSON type; callers do .get("key"), so keep
        # only dict entries and let a bare "sk-..." string mean "not
        # logged in" instead of an AttributeError.
        if isinstance(loaded, dict):
            auth = {k: v for k, v in loaded.items() if isinstance(v, dict)}
    except (OSError, ValueError):
        pass
    # Opened read-only: the CLI holds the database in WAL mode and keeps
    # running, so a lock timeout must degrade to the file's values rather
    # than fail the caller. pathname2url escapes "#", "%" and friends,
    # which would otherwise parse as URI fragments or bad escapes.
    db = os.path.join(_base(), "opencode", "opencode.db")
    try:
        con = sqlite3.connect(
            "file:" + urllib.request.pathname2url(db) + "?mode=ro",
            uri=True, timeout=5)
        try:
            for integration, value in con.execute(
                    "SELECT integration_id, value FROM credential"):
                try:
                    entry = json.loads(value)
                except (TypeError, ValueError):
                    continue
                if isinstance(entry, dict) and isinstance(entry.get("key"), str):
                    auth[integration] = entry
        finally:
            con.close()
    except (OSError, sqlite3.Error):
        pass
    return auth
