"""Durable reservation, response replay and draft CAS extracted from B 6da99f015.

This log has no generation route, controller, role roster or publication state.
Host-issued tasks name local write keys; model responses contain only their
section data. Reservations and deadlines survive restart without refunds.
"""
from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Any, Iterator
from uuid import uuid4
from common.agentic_decision_authority import canonical_digest
from common.semantic_materialization import MaterializationError

DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
READONLY_STREAM_INTERRUPTED = "readonly-stream-interrupted"
BOUNDED_TRANSPORT_ERROR = "bounded-generation-transport-error"

def _deadline_expired(run: Any) -> bool:
    # -1 records explicit wall_seconds=0 for NEW runs, never serialized infinity.
    # Existing deadline=0 remains expired; old journal semantics are unchanged.
    return run["deadline"] != -1 and time.time() >= run["deadline"]


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _name(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise MaterializationError("journal-input", field, "A nonempty identity is required")
    return value


def _digest(value: str, field: str) -> str:
    if type(value) is not str or not DIGEST.fullmatch(value):
        raise MaterializationError("journal-digest", field, "Expected a SHA-256 identity")
    return value


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise MaterializationError("journal-budget", field, "Expected a bounded nonnegative integer")
    return value


def retryable_transport_failure(row: Any) -> bool:
    return row["state"] == "FAILED_CONFIRMED" or (
        row["state"] == "AMBIGUOUS" and row["error_code"] in {READONLY_STREAM_INTERRUPTED, BOUNDED_TRANSPORT_ERROR})


class GenerationJournal:
    """Trusted local accounting; never exposed as model tools."""

    def __init__(self, root: Path, *, replay_settled_only: bool = False) -> None:
        self.replay_settled_only = replay_settled_only
        self.root = Path(root).absolute()
        current = Path(self.root.anchor)
        for part in self.root.parts[1:]:
            current /= part
            if current.is_symlink():
                raise MaterializationError("unsafe-journal-path", "", "Journal paths cannot traverse symbolic links")
        if not replay_settled_only:
            self.root.mkdir(parents=True, mode=0o700, exist_ok=True)
        if not self.root.is_dir():
            raise MaterializationError("unsafe-journal-path", "", "Journal root must be a directory")
        self.path = self.root / "generation.sqlite3"
        for path in (self.path, Path(str(self.path) + "-wal"), Path(str(self.path) + "-shm")):
            if path.is_symlink():
                raise MaterializationError("unsafe-journal-path", "", "Journal database cannot be a symbolic link")
        if replay_settled_only:
            # Frozen replay must not migrate the database or create/remove WAL
            # sidecars. A live WAL cannot be read with immutable=1: require its
            # writer to close/checkpoint before selecting it as frozen evidence.
            wal = Path(str(self.path) + "-wal")
            if not self.path.is_file() or (wal.exists() and wal.stat().st_size):
                raise MaterializationError("journal-not-frozen", "", "Replay requires an existing checkpointed Journal")
            self.db = sqlite3.connect(self.path.as_uri() + "?mode=ro&immutable=1", isolation_level=None, timeout=30, uri=True)
            self.db.row_factory = sqlite3.Row
            if "raw_response" not in {r[1] for r in self.db.execute("PRAGMA table_info(calls)")}:
                self.db.close()
                raise MaterializationError("journal-schema", "", "Existing journal needs explicit migration, never reset")
            return
        self.db = sqlite3.connect(str(self.path), isolation_level=None, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS runs(
                run_id TEXT PRIMARY KEY, phase TEXT NOT NULL, snapshot TEXT NOT NULL,
                scenario_digest TEXT NOT NULL, contract_digest TEXT NOT NULL, max_calls INTEGER NOT NULL,
                max_tokens INTEGER NOT NULL, deadline REAL NOT NULL, version INTEGER NOT NULL DEFAULT 0,
                reserved_calls INTEGER NOT NULL DEFAULT 0, reserved_tokens INTEGER NOT NULL DEFAULT 0,
                state TEXT NOT NULL DEFAULT 'ACTIVE');
            CREATE TABLE IF NOT EXISTS tasks(
                run_id TEXT NOT NULL REFERENCES runs(run_id), task_id TEXT NOT NULL,
                role TEXT NOT NULL, base_version INTEGER NOT NULL, config TEXT NOT NULL,
                PRIMARY KEY(run_id,task_id));
            CREATE TABLE IF NOT EXISTS calls(
                call_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, task_id TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL, dispatch_attempt_id TEXT NOT NULL, reservation INTEGER NOT NULL,
                state TEXT NOT NULL, payload TEXT, raw_response TEXT, payload_digest TEXT, event_digest TEXT,
                usage_tokens INTEGER, error_code TEXT, local_pid INTEGER, local_pgid INTEGER,
                FOREIGN KEY(run_id,task_id) REFERENCES tasks(run_id,task_id),
                UNIQUE(run_id,dispatch_attempt_id));
            CREATE TABLE IF NOT EXISTS draft_units(
                run_id TEXT NOT NULL REFERENCES runs(run_id), handle TEXT NOT NULL,
                value TEXT NOT NULL, version INTEGER NOT NULL, PRIMARY KEY(run_id,handle));
            CREATE TABLE IF NOT EXISTS draft_commits(
                call_id TEXT PRIMARY KEY REFERENCES calls(call_id), request_digest TEXT NOT NULL,
                version INTEGER NOT NULL, receipt TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS call_failures(
                call_id TEXT PRIMARY KEY REFERENCES calls(call_id), task_local INTEGER NOT NULL,
                remote_completed INTEGER NOT NULL, remote_nonexecution INTEGER NOT NULL,
                code TEXT NOT NULL, usage_tokens INTEGER);
            CREATE TABLE IF NOT EXISTS events(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
                event_kind TEXT NOT NULL, body TEXT NOT NULL, recorded_at REAL NOT NULL);
        ''')
        columns = {r[1] for r in self.db.execute("PRAGMA table_info(calls)")}
        if "raw_response" not in columns:
            self.db.close()
            raise MaterializationError("journal-schema", "", "Existing journal needs explicit migration, never reset")
        self.db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS runs_exact_input_identity ON runs(phase,snapshot,contract_digest)"
        )
        self.db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS runs_single_scenario_budget ON runs(phase,scenario_digest)"
        )
        os.chmod(self.path, 0o600)

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "GenerationJournal":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    @contextmanager
    def _tx(self) -> Iterator[None]:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        else:
            self.db.execute("COMMIT")

    def _event(self, run_id: str, kind: str, value: Any) -> None:
        self.db.execute("INSERT INTO events(run_id,event_kind,body,recorded_at) VALUES(?,?,?,?)",
                        (run_id, kind, _json(value), time.time()))

    def _terminalize_active_run(self, run_id: str, *, state: str, reason: str,
                                detail: dict[str, Any] | None = None) -> bool:
        """Transition ACTIVE -> one durable terminal state inside the caller's tx."""
        run = self._run(run_id)
        if run["state"] != "ACTIVE":
            return False
        now = time.time()
        self.db.execute("UPDATE runs SET state=? WHERE run_id=? AND state='ACTIVE'", (state, run_id))
        body = {
            "state": state,
            "reason": reason,
            "remaining_active_wall": max(0.0, float(run["deadline"]) - now) if run["deadline"] != -1 else None,
            "reserved_calls": int(run["reserved_calls"]),
            "reserved_tokens": int(run["reserved_tokens"]),
            "max_calls": int(run["max_calls"]),
            "max_tokens": int(run["max_tokens"]),
            **(detail or {}),
        }
        self._event(run_id, "run-terminal", body)
        return True

    def _run(self, run_id: str) -> sqlite3.Row:
        row = self.db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise MaterializationError("unknown-run", "", "Unknown generation run")
        return row

    def _call(self, call_id: str) -> sqlite3.Row:
        row = self.db.execute("SELECT * FROM calls WHERE call_id=?", (call_id,)).fetchone()
        if row is None:
            raise MaterializationError("unknown-call", "", "Unknown generation call")
        return row

    def create_run(self, *, run_id: str, phase: str, snapshot_digest: str,
                   contract_digest: str, max_calls: int, max_tokens: int,
                   wall_seconds: int,
                   scenario_digest: str | None = None,
                   budget_policy: str = "reserved",
                   review_reservations: dict[str, int] | None = None) -> dict:
        _name(run_id, "run_id")
        if budget_policy not in {"reserved", "charged-pending"}:
            raise MaterializationError("journal-budget", "budget_policy", "Unknown accounting policy")
        if phase not in {"P1", "P2", "P3"}:
            raise MaterializationError("journal-phase", "phase", "Only P1/P2/P3 generation is supported")
        _digest(snapshot_digest, "snapshot_digest"); _digest(contract_digest, "contract_digest")
        resolved_scenario_digest = scenario_digest or snapshot_digest
        _digest(resolved_scenario_digest, "scenario_digest")
        for name, value in (("max_calls", max_calls), ("max_tokens", max_tokens)):
            _integer(value, name, 1)
        _integer(wall_seconds, "wall_seconds", 0)
        review_reservations = review_reservations or {}
        for key, tokens in review_reservations.items():
            _name(key, "review_key"); _integer(tokens, "review_tokens", 1)
        if sum(review_reservations.values()) > max_tokens or len(review_reservations) > max_calls:
            raise MaterializationError("review-reservation", "", "Planned reviews exceed the declared run budget")
        with self._tx():
            if self.db.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone():
                raise MaterializationError("run-exists", "", "A run cannot be recreated to reset its budget")
            same_scenario = self.db.execute(
                "SELECT run_id FROM runs WHERE phase=? AND scenario_digest=?", (phase, resolved_scenario_digest)
            ).fetchone()
            if same_scenario is not None:
                raise MaterializationError(
                    "scenario-run-exists", "",
                    f"This base semantic scenario already belongs to durable run {same_scenario['run_id']}; context completion cannot reset its budget in this workflow version",
                )
            same_input = self.db.execute(
                "SELECT run_id FROM runs WHERE phase=? AND snapshot=? AND contract_digest=?",
                (phase, snapshot_digest, contract_digest),
            ).fetchone()
            if same_input is not None:
                raise MaterializationError(
                    "run-identity-exists", "",
                    f"The exact admitted input already belongs to durable run {same_input['run_id']}; reuse it instead of resetting budget",
                )
            self.db.execute(
                "INSERT INTO runs(run_id,phase,snapshot,scenario_digest,contract_digest,max_calls,max_tokens,deadline) VALUES(?,?,?,?,?,?,?,?)",
                (run_id, phase, snapshot_digest, resolved_scenario_digest, contract_digest, max_calls, max_tokens,
                 time.time() + wall_seconds if wall_seconds else -1.0),
            )
            self._event(run_id, "run-created", {"phase": phase, "snapshot_digest": snapshot_digest,
                        "contract_digest": contract_digest, "max_calls": max_calls, "max_tokens": max_tokens, "wall_seconds": wall_seconds,
                        "budget_policy": budget_policy, "review_reservations": review_reservations})
        return self.status(run_id)

    def create_task(self, *, run_id: str, task_id: str, role: str, base_version: int,
                    read_versions: dict[str, int], write_key: str | None,
                    prompt_digest: str, max_attempts: int, transport_scope: str | None = None,
                    review_key: str | None = None, unprotected_review: bool = False) -> dict:
        _name(task_id, "task_id"); _name(role, "role")
        _integer(base_version, "base_version"); _integer(max_attempts, "max_attempts", 1)
        _digest(prompt_digest, "prompt_digest")
        if type(read_versions) is not dict:
            raise MaterializationError("journal-task", "", "Read versions must be explicit")
        for key, version in read_versions.items():
            _name(key, "read_key"); _integer(version, "read_version")
        if write_key is not None:
            _name(write_key, "write_key")
        config = {"read_versions": read_versions, "write_key": write_key,
                  "prompt_digest": prompt_digest, "max_attempts": max_attempts}
        if unprotected_review:
            if role not in {"omr", "sqr"} or review_key is not None:
                raise MaterializationError("review-reservation", "", "Unprotected review cannot name a protected slot")
            config["unprotected_review"] = True
        if review_key is not None:
            if role not in {"omr", "sqr"} or review_key not in self.review_reservations(run_id):
                raise MaterializationError("review-reservation", "", "Review task must name its declared reservation")
            config["review_key"] = review_key
        if transport_scope is not None:
            _name(transport_scope, "transport_scope")
            if max_attempts != 2:
                raise MaterializationError("transport-scope", "", "Bounded generation allows one transport resend")
            config["transport_scope"] = transport_scope
        with self._tx():
            run = self._run(run_id)
            if self.authors_stopped(run_id) and role not in {"omr", "sqr"}:
                raise MaterializationError("authors-stopped", "", "Human stop-loss retains the funded reviews only")
            if (self.review_reservations(run_id) and role in {"omr", "sqr"}
                    and review_key is None and not unprotected_review):
                raise MaterializationError("review-reservation", "", "An undeclared review cannot consume protected funds")
            if review_key is not None:
                if any(review_key in json.loads(row["body"])["keys"] for row in self.db.execute(
                        "SELECT body FROM events WHERE run_id=? AND event_kind='review-slots-released'", (run_id,))):
                    raise MaterializationError("review-reservation", "", "Actual grouping released this unused slot")
                for issued in self.db.execute("SELECT task_id,config FROM tasks WHERE run_id=?", (run_id,)):
                    if issued["task_id"] != task_id and json.loads(issued["config"]).get("review_key") == review_key:
                        raise MaterializationError("review-reservation", "", "Review reservation already belongs to another task")
            old = self.db.execute("SELECT * FROM tasks WHERE run_id=? AND task_id=?", (run_id, task_id)).fetchone()
            if old:
                if (old["role"], old["base_version"], old["config"]) != (role, base_version, _json(config)):
                    raise MaterializationError("task-conflict", "", "Issued scope and attempt limit are immutable")
            else:
                if self.replay_settled_only or run["state"] != "ACTIVE" or base_version != run["version"]:
                    raise MaterializationError("stale-task", "", "No new task outside its active parent")
                self._check_reads(run_id, read_versions)
                self.db.execute("INSERT INTO tasks VALUES(?,?,?,?,?)", (run_id, task_id, role, base_version, _json(config)))
                self._event(run_id, "task-created", {"task_id": task_id, "role": role, **config})
        return {"run_id": run_id, "task_id": task_id, "role": role, "base_version": base_version, **deepcopy(config)}

    def reserve_call(self, *, run_id: str, task_id: str, dispatch_attempt_id: str,
                     token_reservation: int) -> dict:
        _integer(token_reservation, "token_reservation", 1)
        _name(dispatch_attempt_id, "dispatch_attempt_id")
        terminal_error: tuple[str, str] | None = None
        result: dict[str, Any] | None = None
        with self._tx():
            run = self._run(run_id)
            old = self.db.execute("SELECT * FROM calls WHERE run_id=? AND dispatch_attempt_id=?", (run_id, dispatch_attempt_id)).fetchone()
            if old:
                if old["task_id"] != task_id or old["reservation"] != token_reservation:
                    raise MaterializationError("attempt-conflict", "", "A dispatch-attempt key cannot be reused with different parameters")
                if self.replay_settled_only and old["state"] != "SETTLED":
                    raise MaterializationError("settled-replay-only", "", "Read-only replay requires already settled responses")
                return self._call_identity(old)
            if self.replay_settled_only:
                raise MaterializationError("settled-replay-only", "", "Read-only replay cannot reserve new calls")
            task = self.db.execute("SELECT * FROM tasks WHERE run_id=? AND task_id=?", (run_id, task_id)).fetchone()
            if task is None:
                raise MaterializationError("unknown-task", "", "A Workflow-issued task is required")
            if run["state"] != "ACTIVE":
                raise MaterializationError("run-stopped", "", "Stopped or ambiguous runs cannot dispatch replacement calls")
            if task["base_version"] != run["version"]:
                raise MaterializationError("stale-task", "", "Task parent changed before dispatch")
            self._check_reads(run_id, json.loads(task["config"])["read_versions"])
            attempts = self.db.execute("SELECT * FROM calls WHERE run_id=? AND task_id=?", (run_id, task_id)).fetchall()
            if self.authors_stopped(run_id) and task["role"] not in {"omr", "sqr"}:
                raise MaterializationError("authors-stopped", "", "Human stop-loss retains the funded reviews only")
            unused = self.unused_review_reservations(run_id)
            own_key = json.loads(task["config"]).get("review_key")
            protected = {key: value for key, value in unused.items() if key != own_key}
            protected_tokens = sum(protected.values())
            if own_key in unused and token_reservation > unused[own_key]:
                raise MaterializationError("review-reservation", "", "Review request exceeds its declared reservation")
            if any(not retryable_transport_failure(row) for row in attempts):
                raise MaterializationError("task-attempt-exists", "", "Recover the original attempt; pending or completed work must not be re-issued")
            if len(attempts) >= json.loads(task["config"])["max_attempts"]:
                self._terminalize_active_run(
                    run_id, state="RETRY_EXHAUSTED", reason="transport-retry-exhausted",
                    detail={"pending_task_id": task_id, "attempt_count": len(attempts)},
                )
                terminal_error = ("task-retry-exhausted", "The bounded transport retry allowance is exhausted")
            elif _deadline_expired(run):
                self._terminalize_active_run(
                    run_id, state="DEADLINE_EXCEEDED", reason="deadline-before-call-reservation",
                    detail={"pending_task_id": task_id, "requested_reservation": token_reservation},
                )
                terminal_error = ("deadline-exceeded", "Frozen run wall deadline expired before call reservation")
            elif self.review_reservations(run_id) and (
                    run["reserved_calls"] + 1 + len(protected) > run["max_calls"]
                    or self._budget_used(run) + token_reservation + protected_tokens > run["max_tokens"]):
                # A failed author reservation must not terminalize already funded reviews.
                if task["role"] not in {"omr", "sqr"}:
                    self._event(run_id, "authors-stopped", {"reason": "protected-review-budget",
                        "task_id": task_id, "requested_reservation": token_reservation,
                        "unused_review_tokens": protected_tokens})
                terminal_error = ("protected-review-budget", "Call cannot consume unused planned review reservations")
            elif (run["reserved_calls"] + 1 > run["max_calls"]
                  or self._budget_used(run) + token_reservation > run["max_tokens"]):
                self._terminalize_active_run(
                    run_id, state="BUDGET_EXHAUSTED", reason="reservation-budget-exhausted",
                    detail={"pending_task_id": task_id, "requested_reservation": token_reservation},
                )
                terminal_error = ("budget-exhausted", "Frozen run call/token reservation budget exhausted")
            else:
                call_id, token = uuid4().hex, uuid4().hex
                self.db.execute("INSERT INTO calls(call_id,run_id,task_id,token,dispatch_attempt_id,reservation,state) VALUES(?,?,?,?,?,?, 'RESERVED')",
                                (call_id, run_id, task_id, token, dispatch_attempt_id, token_reservation))
                self.db.execute("UPDATE runs SET reserved_calls=reserved_calls+1,reserved_tokens=reserved_tokens+? WHERE run_id=?", (token_reservation, run_id))
                self._event(run_id, "call-reserved", {"call_id": call_id, "task_id": task_id,
                            "dispatch_attempt_id": dispatch_attempt_id, "reservation": token_reservation})
                result = self._call_identity(self._call(call_id))
        if terminal_error is not None:
            raise MaterializationError(terminal_error[0], "", terminal_error[1])
        assert result is not None
        return result

    def mark_dispatched(self, call_id: str) -> None:
        terminal_error: tuple[str, str] | None = None
        with self._tx():
            call = self._call(call_id); run = self._run(call["run_id"])
            if call["state"] != "RESERVED" or run["state"] != "ACTIVE":
                raise MaterializationError("dispatch-state", "", "Call may be dispatched exactly once within its active budget")
            if _deadline_expired(run):
                self.db.execute("INSERT INTO call_failures VALUES(?,?,?,?,?,?)",
                                (call_id, 0, 0, 1, "wall-deadline-before-dispatch", None))
                self.db.execute("UPDATE calls SET state='FAILED_CONFIRMED',error_code=? WHERE call_id=?",
                                ("wall-deadline-before-dispatch", call_id))
                self._event(call["run_id"], "call-failed", {
                    "call_id": call_id, "state": "FAILED_CONFIRMED",
                    "code": "wall-deadline-before-dispatch", "usage_tokens": None,
                    "task_local": False,
                })
                self._terminalize_active_run(
                    call["run_id"], state="DEADLINE_EXCEEDED", reason="deadline-at-dispatch-cas",
                    detail={"pending_task_id": call["task_id"], "call_id": call_id},
                )
                terminal_error = ("deadline-exceeded", "Run wall deadline expired before adapter dispatch")
            else:
                task = self.db.execute("SELECT * FROM tasks WHERE run_id=? AND task_id=?", (call["run_id"], call["task_id"])).fetchone()
                if task["base_version"] != run["version"]:
                    raise MaterializationError("stale-task", "", "Task parent changed after reservation; do not send stale work")
                self._check_reads(call["run_id"], json.loads(task["config"])["read_versions"])
                if self.authors_stopped(call["run_id"]) and task["role"] not in {"omr", "sqr"}:
                    self.db.execute("UPDATE calls SET state='FAILED_CONFIRMED',usage_tokens=0,error_code='authors-stopped' WHERE call_id=?", (call_id,))
                    self._event(call["run_id"], "call-failed", {"call_id":call_id, "code":"authors-stopped", "usage_tokens":0})
                    terminal_error = ("authors-stopped", "Author stopped before transport; funded reviews remain runnable")
                else:
                    self.db.execute("UPDATE calls SET state='DISPATCHED' WHERE call_id=?", (call_id,))
                    self._event(call["run_id"], "call-dispatched", {"call_id": call_id})
        if terminal_error is not None:
            raise MaterializationError(terminal_error[0], "", terminal_error[1])

    def remaining_wall_seconds(self, run_id: str) -> float:
        """Return the current durable wall allowance; this is not a new budget."""
        run = self._run(run_id)
        return max(0.0, float(run["deadline"]) - time.time()) if run["deadline"] != -1 else float("inf")

    def bind_local_process(self, *, call_id: str, pid: int, pgid: int) -> None:
        _integer(pid, "pid", 1); _integer(pgid, "pgid", 1)
        with self._tx():
            call = self._call(call_id)
            if call["state"] != "DISPATCHED":
                raise MaterializationError("process-state", "", "Local process may bind only to a dispatched call")
            if call["local_pid"] is not None and (call["local_pid"], call["local_pgid"]) != (pid, pgid):
                raise MaterializationError("process-conflict", "", "A dispatched call cannot change local process identity")
            self.db.execute("UPDATE calls SET local_pid=?,local_pgid=? WHERE call_id=?", (pid, pgid, call_id))
            self._event(call["run_id"], "local-process-bound", {"call_id": call_id, "pid": pid, "pgid": pgid})

    def record_response(self, *, call_id: str, run_id: str, task_id: str,
                        request_token: str, payload: Any, event_digest: str,
                        usage_tokens: int | None = None, raw_response: str | None = None) -> dict:
        _digest(event_digest, "event_digest")
        if usage_tokens is not None: _integer(usage_tokens, "usage_tokens")
        if raw_response is not None and type(raw_response) is not str:
            raise MaterializationError("raw-response", "", "Raw response must be unchanged text")
        body = _json(payload); body_digest = canonical_digest(payload)
        with self._tx():
            call = self._call(call_id)
            if (call["run_id"], call["task_id"], call["token"]) != (run_id, task_id, request_token):
                raise MaterializationError("response-identity", "", "Response does not belong to this issued call")
            if call["state"] in {"RESPONSE_RECORDED", "SETTLED"}:
                if (call["payload_digest"], call["event_digest"], call["usage_tokens"], call["raw_response"]) != (body_digest, event_digest, usage_tokens, raw_response):
                    raise MaterializationError("response-conflict", "", "A completed response cannot be replaced")
            elif call["state"] == "DISPATCHED":
                self.db.execute("UPDATE calls SET state='RESPONSE_RECORDED',payload=?,payload_digest=?,event_digest=?,usage_tokens=?,raw_response=? WHERE call_id=?",
                                (body, body_digest, event_digest, usage_tokens, raw_response, call_id))
                self._event(run_id, "response-recorded", {"call_id": call_id, "payload_digest": body_digest, "event_digest": event_digest, "usage_tokens": usage_tokens})
                if _deadline_expired(self._run(run_id)):
                    self.db.execute("UPDATE runs SET state='DEADLINE_EXCEEDED' WHERE run_id=? AND state='ACTIVE'", (run_id,))
                    self._event(run_id, "late-response-retained", {"call_id": call_id})
                run = self._run(run_id)
                exceeds_estimate = usage_tokens is not None and usage_tokens > call["reservation"]
                charged_pending = self.budget_policy(run_id) == "charged-pending"
                if exceeds_estimate:
                    self._event(run_id, "reservation-estimate-exceeded", {"call_id": call_id,
                        "observed": usage_tokens, "reserved": call["reservation"]})
                # Measured settlement may exceed an estimate without exceeding the
                # declared run budget. Preserve the actual charge and pending calls;
                # never replace or enlarge the original reservation.
                if ((charged_pending and self._budget_used(run) > run["max_tokens"])
                        or (not charged_pending and exceeds_estimate)):
                    self.db.execute("UPDATE runs SET state='BUDGET_OVERRUN' WHERE run_id=? AND state='ACTIVE'", (run_id,))
                    self._event(run_id, "budget-overrun", {"call_id": call_id,
                        "observed": usage_tokens, "reserved": call["reservation"]})
            else:
                raise MaterializationError("response-state", "", "Only the original dispatched call can record a response")
        return {"call_id": call_id, "payload_digest": body_digest, "event_digest": event_digest, "authority_created": False}

    def settle(self, call_id: str) -> None:
        with self._tx():
            call = self._call(call_id)
            if call["state"] not in {"RESPONSE_RECORDED", "SETTLED"}:
                raise MaterializationError("settlement-state", "", "Only a retained response can be settled")
            if call["state"] != "SETTLED":
                self.db.execute("UPDATE calls SET state='SETTLED' WHERE call_id=?", (call_id,))
                self._event(call["run_id"], "call-settled", {"call_id": call_id})

    def transport_failure_counts(self, run_id: str, scope: str) -> dict:
        """Durable counts across semantic repairs and reopened local connections."""
        rows = self.db.execute(
            "SELECT t.config FROM calls c JOIN tasks t ON c.run_id=t.run_id AND c.task_id=t.task_id "
            "WHERE c.run_id=? AND c.error_code=?", (run_id, BOUNDED_TRANSPORT_ERROR),
        ).fetchall()
        return {"run": len(rows), "section": sum(json.loads(r["config"]).get("transport_scope") == scope for r in rows)}

    def fail_call(self, call_id: str, *, code: str,
                  remote_nonexecution_confirmed: bool = False,
                  remote_execution_completed: bool = False,
                  usage_tokens: int | None = None) -> None:
        """Record host-verified transport facts; do not choose section repair policy."""
        _name(code, "code")
        if any(type(v) is not bool for v in (remote_nonexecution_confirmed, remote_execution_completed)):
            raise MaterializationError("journal-input", "", "Failure flags must be boolean")
        if remote_nonexecution_confirmed and remote_execution_completed:
            raise MaterializationError("journal-input", "", "Execution cannot be absent and completed")
        if usage_tokens is not None:
            _integer(usage_tokens, "usage_tokens")
        with self._tx():
            call = self._call(call_id)
            if code == READONLY_STREAM_INTERRUPTED and (call["state"] == "RESERVED" or
                    remote_nonexecution_confirmed or remote_execution_completed or usage_tokens is not None):
                raise MaterializationError("failure-scope", "", "Interrupted stream cannot claim completion or usage")
            if code == BOUNDED_TRANSPORT_ERROR:
                task = self.db.execute("SELECT config FROM tasks WHERE run_id=? AND task_id=?",
                                       (call["run_id"], call["task_id"])).fetchone()
                config = json.loads(task["config"])
                if (call["state"] == "RESERVED" or remote_nonexecution_confirmed or remote_execution_completed
                        or usage_tokens != call["reservation"] or not config.get("transport_scope")
                        or config["max_attempts"] != 2):
                    raise MaterializationError("failure-scope", "", "Transport uncertainty consumes the full bounded reservation")
            flags = (0, int(remote_execution_completed), int(remote_nonexecution_confirmed), code, usage_tokens)
            if call["state"] not in {"RESERVED", "DISPATCHED"}:
                saved = self.db.execute("SELECT task_local,remote_completed,remote_nonexecution,code,usage_tokens FROM call_failures WHERE call_id=?", (call_id,)).fetchone()
                if saved is not None and tuple(saved) == flags:
                    return
                raise MaterializationError("failure-state", "", "Final failure facts cannot be replaced")
            if call["state"] == "RESERVED" and remote_execution_completed:
                raise MaterializationError("failure-scope", "", "Undispatched call cannot have completed")
            state = ("FAILED_CONFIRMED" if call["state"] == "RESERVED" or remote_nonexecution_confirmed
                     else "FAILED_FINAL" if remote_execution_completed else "AMBIGUOUS")
            self.db.execute("INSERT INTO call_failures VALUES(?,?,?,?,?,?)", (call_id, *flags))
            self.db.execute("UPDATE calls SET state=?,error_code=?,usage_tokens=? WHERE call_id=?", (state, code, usage_tokens, call_id))
            run = self._run(call["run_id"])
            terminal = ("BUDGET_OVERRUN" if usage_tokens is not None and usage_tokens > call["reservation"]
                        else "DEADLINE_EXCEEDED" if _deadline_expired(run)
                        else "TRANSPORT_ERRORS_EXHAUSTED" if code == BOUNDED_TRANSPORT_ERROR
                        and self.transport_failure_counts(call["run_id"], config["transport_scope"])["run"] >= 3
                        else "AMBIGUOUS" if state == "AMBIGUOUS" and code not in {READONLY_STREAM_INTERRUPTED, BOUNDED_TRANSPORT_ERROR} else None)
            if terminal:
                self._terminalize_active_run(call["run_id"], state=terminal, reason=code)
            self._event(call["run_id"], "call-failed", {"call_id": call_id, "state": state, "code": code, "usage_tokens": usage_tokens})

    def recover(self, run_id: str) -> dict:
        """Call after the Workflow establishes no old local dispatcher is running.

        Never re-dispatch possibly-sent work. Provider reconciliation is outside
        this journal until a transport can supply verified original-call proof.
        """
        with self._tx():
            self._run(run_id)
            rows = self.db.execute(
                "SELECT call_id,local_pgid FROM calls WHERE run_id=? AND state='DISPATCHED'", (run_id,)
            ).fetchall()
            if rows:
                for row in rows:
                    pgid = row["local_pgid"]
                    if not pgid or not sys.platform.startswith("linux"):
                        continue
                    try:
                        os.killpg(int(pgid), 0)
                    except ProcessLookupError:
                        continue
                    except PermissionError as exc:
                        raise MaterializationError(
                            "recovery-process", "", "Cannot prove the old dispatched process group has stopped"
                        ) from exc
                    raise MaterializationError(
                        "recovery-process", "", "Old dispatched process group is still alive; cleanup is required before recovery"
                    )
                self.db.execute("UPDATE calls SET state='AMBIGUOUS',error_code='recovery-remote-unknown' WHERE run_id=? AND state='DISPATCHED'", (run_id,))
                self.db.execute("UPDATE runs SET state='AMBIGUOUS' WHERE run_id=?", (run_id,))
                self._event(run_id, "recovery-ambiguous", {"call_ids": [r["call_id"] for r in rows]})
        return self.status(run_id)

    def commit_draft(self, *, call_id: str, expected_version: int) -> dict:
        """CAS one retained section under the host-issued key; no model handles."""
        _integer(expected_version, "expected_version")
        with self._tx():
            call = self._call(call_id)
            if call["state"] not in {"RESPONSE_RECORDED", "SETTLED"}:
                raise MaterializationError("draft-response", "", "Commit requires a retained response")
            request_digest = canonical_digest({"response": call["payload_digest"], "parent": expected_version})
            prior = self.db.execute("SELECT * FROM draft_commits WHERE call_id=?", (call_id,)).fetchone()
            if prior:
                if prior["request_digest"] != request_digest:
                    raise MaterializationError("draft-replay-conflict", "", "Same call cannot change its parent")
                return json.loads(prior["receipt"])
            task = self.db.execute("SELECT * FROM tasks WHERE run_id=? AND task_id=?", (call["run_id"], call["task_id"])).fetchone()
            config = json.loads(task["config"]); run = self._run(call["run_id"])
            if config["write_key"] is None:
                raise MaterializationError("write-scope", "", "Read-only task cannot commit")
            if _deadline_expired(run):
                raise MaterializationError("deadline-exceeded", "", "Late evidence cannot create a usable draft")
            if run["state"] != "ACTIVE" or expected_version != run["version"] or expected_version != task["base_version"]:
                raise MaterializationError("stale-draft", "", "Parent changed; no implicit rebase")
            self._check_reads(call["run_id"], config["read_versions"])
            version = run["version"] + 1
            self.db.execute("INSERT INTO draft_units VALUES(?,?,?,?) ON CONFLICT(run_id,handle) DO UPDATE SET value=excluded.value,version=excluded.version",
                            (call["run_id"], config["write_key"], call["payload"], version))
            receipt = {"call_id": call_id, "previous_version": expected_version, "draft_version": version,
                       "response_digest": call["payload_digest"], "authority_created": False, "state": "DRAFT_ONLY"}
            self.db.execute("UPDATE runs SET version=? WHERE run_id=?", (version, call["run_id"]))
            self.db.execute("INSERT INTO draft_commits VALUES(?,?,?,?)", (call_id, request_digest, version, _json(receipt)))
            self._event(call["run_id"], "draft-committed", receipt)
        return receipt

    def status(self, run_id: str) -> dict:
        # An explicit WAL read snapshot prevents a torn run/call/unit view while
        # another Workflow connection commits. No role credentials are returned.
        self.db.execute("BEGIN")
        try:
            run = dict(self._run(run_id))
            calls = self.db.execute("SELECT call_id,task_id,dispatch_attempt_id,state,reservation,payload_digest,event_digest,usage_tokens,error_code,local_pid,local_pgid FROM calls WHERE run_id=? ORDER BY rowid", (run_id,)).fetchall()
            units = self.db.execute("SELECT handle,value,version FROM draft_units WHERE run_id=? ORDER BY handle", (run_id,)).fetchall()
            result = {"run": run, "calls": [dict(r) for r in calls],
                      "draft_units": {r["handle"]: {"value": json.loads(r["value"]), "version": r["version"]} for r in units},
                      "authority_created": False}
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def replay_response(self, call_id: str) -> dict:
        call = self._call(call_id)
        if call["state"] != "SETTLED":
            raise MaterializationError("replay-unsettled", "", "Replay requires a settled response")
        return {"payload": json.loads(call["payload"]), "raw_response": call["raw_response"],
                "payload_digest": call["payload_digest"], "event_digest": call["event_digest"]}

    def review_reservations(self, run_id: str) -> dict[str, int]:
        event = self.db.execute("SELECT body FROM events WHERE run_id=? AND event_kind='run-created' ORDER BY sequence LIMIT 1",
                                (run_id,)).fetchone()
        return json.loads(event["body"]).get("review_reservations", {}) if event else {}

    def unused_review_reservations(self, run_id: str) -> dict[str, int]:
        # Called under the same BEGIN IMMEDIATE as the pending call reservation.
        configs = self.db.execute("SELECT DISTINCT t.config FROM tasks t JOIN calls c "
            "ON c.run_id=t.run_id AND c.task_id=t.task_id WHERE t.run_id=?", (run_id,)).fetchall()
        used = {json.loads(row["config"]).get("review_key") for row in configs}
        released = {key for row in self.db.execute("SELECT body FROM events WHERE run_id=? AND event_kind='review-slots-released'", (run_id,))
                    for key in json.loads(row["body"])["keys"]}
        return {key: value for key, value in self.review_reservations(run_id).items() if key not in used | released}

    def release_review_reservations(self, run_id: str, *, keys: list[str], reason: str) -> None:
        """Release unused slots only after actual-size grouping reduces packet count."""
        if not keys:return
        _name(reason, "reason")
        with self._tx():
            if self._run(run_id)["state"] != "ACTIVE" or self.replay_settled_only:
                raise MaterializationError("run-stopped", "", "Cannot release a frozen run reservation")
            if len(set(keys)) != len(keys) or not set(keys) <= self.unused_review_reservations(run_id).keys():
                raise MaterializationError("review-reservation", "", "Only unused declared review slots can be released")
            self._event(run_id, "review-slots-released", {"keys":keys,"reason":reason})

    def authors_stopped(self, run_id: str) -> bool:
        return self.db.execute("SELECT 1 FROM events WHERE run_id=? AND event_kind='authors-stopped' LIMIT 1",
                               (run_id,)).fetchone() is not None

    def stop_authors(self, run_id: str, *, reason: str) -> None:
        """Persist a human author/repair stop without stopping funded OMR/SQR."""
        _name(reason, "reason")
        with self._tx():
            run = self._run(run_id)
            if run["state"] != "ACTIVE" or self.replay_settled_only:
                raise MaterializationError("run-stopped", "", "Cannot change a terminal/frozen run")
            if not self.authors_stopped(run_id):
                self._event(run_id, "authors-stopped", {"reason": reason})

    def budget_policy(self, run_id: str) -> str:
        """Read the immutable run declaration; old journals retain reservation policy."""
        event = self.db.execute("SELECT body FROM events WHERE run_id=? AND event_kind='run-created' ORDER BY sequence LIMIT 1",
                                (run_id,)).fetchone()
        return json.loads(event["body"]).get("budget_policy", "reserved") if event else "reserved"

    def _budget_used(self, run) -> int:
        # Called inside the reservation's BEGIN IMMEDIATE transaction. Pending or
        # unknown execution keeps its full reservation; only measured settlement
        # or confirmed nonexecution can reduce the accounting amount.
        if self.budget_policy(run["run_id"]) == "reserved":
            return run["reserved_tokens"]
        return self.db.execute("SELECT COALESCE(SUM(CASE WHEN usage_tokens IS NOT NULL THEN usage_tokens "
            "WHEN state='FAILED_CONFIRMED' THEN 0 ELSE reservation END),0) FROM calls WHERE run_id=?",
            (run["run_id"],)).fetchone()[0]

    def accounting(self, run_id: str) -> dict:
        state = self.status(run_id)
        calls = state["calls"]
        unknown = [c["call_id"] for c in calls if c["usage_tokens"] is None and c["state"] != "FAILED_CONFIRMED"]
        conservative_ids = []
        for call in calls:
            payload = self._call(call["call_id"])["payload"]
            value = json.loads(payload) if payload else None
            if (call["error_code"] == BOUNDED_TRANSPORT_ERROR
                    or isinstance(value, dict) and value.get("usage_kind") == "caller-cutoff-upper-bound"):
                conservative_ids.append(call["call_id"])
        pending = [c for c in calls if c["state"] in {"RESERVED", "DISPATCHED"}]
        upper_bound = [c for c in calls if c["usage_tokens"] is None
                       and c["state"] not in {"RESERVED", "DISPATCHED", "FAILED_CONFIRMED"}]
        charged = sum(c["usage_tokens"] for c in calls if c["usage_tokens"] is not None)
        conservative = sum(c["usage_tokens"] for c in calls
                           if c["call_id"] in conservative_ids and c["usage_tokens"] is not None)
        if self.budget_policy(run_id) == "charged-pending":
            unknown_charge = sum(c["reservation"] for c in upper_bound)
            charged += unknown_charge; conservative += unknown_charge
            conservative_ids.extend(c["call_id"] for c in upper_bound if c["call_id"] not in conservative_ids)
        return {"budget_policy": self.budget_policy(run_id),
                "unused_review_reservations": self.unused_review_reservations(run_id),
                "unused_review_tokens": sum(self.unused_review_reservations(run_id).values()),
                "authors_stopped": self.authors_stopped(run_id),
                "pending_reserved_tokens": sum(c["reservation"] for c in pending),
                "reserved_calls": state["run"]["reserved_calls"],
                "reserved_tokens": state["run"]["reserved_tokens"],
                "measured_tokens": charged - conservative, "charged_tokens": charged,
                "conservative_tokens": conservative, "conservative_call_ids": conservative_ids,
                "unknown_call_ids": unknown, "total_tokens": None if unknown else charged}

    @staticmethod
    def _call_identity(call: sqlite3.Row) -> dict:
        return {"call_id": call["call_id"], "run_id": call["run_id"], "task_id": call["task_id"],
                "dispatch_attempt_id": call["dispatch_attempt_id"], "request_token": call["token"],
                "reservation": call["reservation"], "state": call["state"]}

    def _check_reads(self, run_id: str, reads: dict[str, int]) -> None:
        for handle, version in reads.items():
            row = self.db.execute("SELECT version FROM draft_units WHERE run_id=? AND handle=?", (run_id, handle)).fetchone()
            if (row["version"] if row else 0) != version:
                raise MaterializationError("stale-read", "", "A read dependency changed before the operation")
