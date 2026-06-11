from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "v0.1"

SUPPORTED_ARTIFACT_TYPES = (
    "REQ",
    "ARCH",
    "BOUNDARY",
    "CAPABILITY",
    "DECISION",
    "DOMAIN",
    "MODULE",
    "SERVICE",
    "ENTITY",
    "EVENT",
    "DEPENDENCY",
    "DATA",
    "SCHEMA",
    "STORAGE",
    "INTERFACE",
    "FLOW",
    "SCENARIO",
    "SECURITY",
    "DEPLOY",
    "PERF",
    "TECHSEL",
    "OPTIMAL",
    "ASSUME",
    "MILESTONE",
    "HANDOFF",
    "PROTOTYPE",
    "SEQUENCE",
    "VERIFY",
    "RISK",
)


@dataclass(frozen=True)
class ProjectScope:
    project_key: str
    project_root: Path

    @property
    def scope_id(self) -> str:
        return f"{self.project_key}:{self.project_root.resolve()}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_db_path(project_root: Path) -> Path:
    return project_root / ".trace" / "trace.db"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def open_db(db_path: Path) -> sqlite3.Connection:
    ensure_parent(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def load_schema_sql(base_dir: Path) -> str:
    schema_path = base_dir / "sql" / "schema.sql"
    return schema_path.read_text(encoding="utf-8")
