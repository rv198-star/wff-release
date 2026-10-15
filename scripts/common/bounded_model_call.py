"""One declared model call: streaming cap, evidence and Journal accounting for D/P3.

One bounded transport resend per section; no semantic decisions or provider schema.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Callable

from common.agentic_decision_authority import canonical_digest
from common.semantic_generation_journal import BOUNDED_TRANSPORT_ERROR, GenerationJournal
from common.semantic_materialization import write_json_exclusive, MaterializationError

MAX_REQUEST_TOKENS = 60_000
MAX_OUTPUT_TOKENS = 8_000
REQUEST_FRAMING_ALLOWANCE = 4_000


class CallBoundary(ValueError):
    """The declared run cannot spend again after a transport/accounting boundary."""


class SectionRejected(ValueError):
    """Only this section needs simplification within its existing repair allowance."""


class TransportError(ValueError):
    """HTTP/stream failure; remote execution is uncertain, charged at its reservation."""


class TransportSectionRejected(SectionRejected):
    """The section's two transport failures require a T2 gap, not content repair."""


def estimate_request_tokens(prompt: str, *, calibrated: bool = True, request_divisor: float = 1.0) -> int:
    """Original conservative bound, optionally divided by an evidenced request ratio."""
    if not math.isfinite(request_divisor) or not 0 < request_divisor <= 1.4:
        raise ValueError("Request divisor must be positive and no greater than the approved1.4")
    size = len(prompt.encode("utf-8"))
    upper = ((size + 1) // 2 if calibrated else size) + REQUEST_FRAMING_ALLOWANCE
    return math.ceil(upper / request_divisor) if calibrated else upper


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compact(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(compact(row) + "\n"); stream.flush(); os.fsync(stream.fileno())


def call_row(context: dict, *, section: str, attempt: int, prompt: str, template_version: str) -> dict:
    return {"run_id": context["run_id"], "wp": context["wp"], "scenario": context["scenario"],
        "section": section, "attempt": attempt, "request_tokens": None, "output_tokens": None,
        "duration_ms": 0, "parse_ok": False, "validate_ok": False, "diagnostics": [],
        "outcome": "failed", "template_version": template_version, "patterns": [],
        "model": context["model"], "prompt_sha256": _sha(prompt),
        "measurement_kind": context["measurement_kind"]}


def dispatch(*, journal: GenerationJournal, context: dict, task_id: str, role: str,
              write_key: str | None, prompt: str, binding: dict, send: Callable,
              output_dir: Path, row: dict, payload_reader: Callable | None = None,
              max_transport_attempts: int = 2, review_key: str | None = None,
              unprotected_review: bool = False) -> tuple[dict, dict, int]:
    """Charge every dispatch, bound transport recovery, and leave content judgment to the caller."""
    if type(max_transport_attempts) is not int or max_transport_attempts not in (1, 2):
        raise ValueError("One initial attempt and at most one transport resend permitted")
    if context["measurement_kind"] not in {"model", "fixture"}:
        raise ValueError("Explicit model or fixture measurement kind required")
    request_bound = getattr(send, "estimate_request_tokens", estimate_request_tokens)(prompt)
    if request_bound > MAX_REQUEST_TOKENS:
        raise SectionRejected("Request bound exceeds60000; split input or simplify before any call")
    metering = getattr(send, "request_estimate_metadata", None)
    if metering is not None:
        row["request_metering"] = metering(prompt)
    scope = row["section"]
    counts = journal.transport_failure_counts(context["run_id"], scope)
    counts["run"] += context.get("prior_transport_errors", 0)
    if counts["run"] >= 3:
        raise CallBoundary("Three transport errors reached; stop the run and report Owner")
    if counts["section"] >= 2:
        raise TransportSectionRejected("Two transport failures in this section; retain a T2 gap")
    state = journal.status(context["run_id"]); version = state["run"]["version"]
    try:
        journal.create_task(run_id=context["run_id"], task_id=task_id, role=role,
            base_version=version, read_versions={}, write_key=write_key,
            prompt_digest="sha256:" + row["prompt_sha256"], max_attempts=2, transport_scope=scope, review_key=review_key,
            unprotected_review=unprotected_review)
    except MaterializationError as exc:
        if journal.authors_stopped(context["run_id"]) and role not in {"omr", "sqr"}:
            raise CallBoundary("Authors stopped; funded reviews remain runnable") from exc
        raise
    seed = dict(row)
    for transport_attempt in range(max_transport_attempts):
        try:
            call = journal.reserve_call(run_id=context["run_id"], task_id=task_id,
                dispatch_attempt_id=task_id + ".dispatch." + str(transport_attempt),
                token_reservation=request_bound + MAX_OUTPUT_TOKENS)
        except MaterializationError as exc:
            if journal.review_reservations(context["run_id"]):
                raise CallBoundary("Protected review/call budget: " + str(exc)) from exc
            raise
        if call["state"] != "RESERVED":
            raise CallBoundary("Existing call must be replayed from its retained evidence, never redispatched")
        folder = output_dir / "calls" / call["call_id"]; folder.mkdir(parents=True, exist_ok=False)
        (folder / "prompt.txt").write_text(prompt, encoding="utf-8")
        row.clear(); row.update(seed)
        row.update(call_id=call["call_id"], prompt_path=str(folder / "prompt.txt"),
                   request_token_bound=request_bound, output_token_limit=MAX_OUTPUT_TOKENS,
                   transport_attempt=transport_attempt, **binding)
        try:
            journal.mark_dispatched(call["call_id"])
        except MaterializationError as exc:
            if journal.authors_stopped(context["run_id"]) and role not in {"omr", "sqr"}:
                raise CallBoundary("Author stopped before transport; funded reviews remain runnable") from exc
            raise
        start = time.monotonic()
        try:
            reply = send(prompt, max_output_tokens=MAX_OUTPUT_TOKENS)
            if not isinstance(reply, dict) or not isinstance(reply.get("raw"), str):
                raise ValueError("Transport must return unchanged response text")
        except TransportError as exc:
            row.update(duration_ms=round((time.monotonic() - start) * 1000),
                       diagnostics=["HTTP/stream error; full reservation conservatively charged"],
                       request_tokens=request_bound, output_tokens=MAX_OUTPUT_TOKENS,
                       provider_request_tokens=None, provider_output_tokens=None,
                       usage_kind="transport-error-upper-bound", remote_execution="unknown",
                       transport_error=True)
            journal.fail_call(call["call_id"], code=BOUNDED_TRANSPORT_ERROR, usage_tokens=call["reservation"])
            counts = journal.transport_failure_counts(context["run_id"], scope)
            counts["run"] += context.get("prior_transport_errors", 0)
            row["transport_error_counts"] = counts
            if counts["section"] >= 2:
                row["outcome"] = "degraded-T2"
            write_json_exclusive(folder / "transport-error.json", {
                "error_type": type(exc).__name__, "usage_kind": row["usage_kind"],
                "charged_tokens": call["reservation"], "remote_execution": "unknown",
                "transport_error_counts": counts})
            append_row(output_dir / "calls.jsonl", row)
            if counts["run"] >= 3:
                raise CallBoundary("Three transport errors reached; stop the run and report Owner") from exc
            if journal.status(context["run_id"])["run"]["state"] != "ACTIVE":
                raise CallBoundary("Journal deadline or declared budget boundary reached") from exc
            if counts["section"] >= 2:
                raise TransportSectionRejected("Two transport failures in this section; retain a T2 gap") from exc
            if transport_attempt + 1 >= max_transport_attempts:
                raise TransportSectionRejected("Declared call allowance leaves no transport resend; retain a T2 gap") from exc
            continue
        except Exception as exc:
            row["duration_ms"] = round((time.monotonic() - start) * 1000)
            row["diagnostics"] = ["Transport execution is unknown: " + type(exc).__name__]
            if journal.budget_policy(context["run_id"]) == "charged-pending":
                row.update(usage_kind="unknown-usage-upper-bound", charged_tokens=call["reservation"],
                           provider_request_tokens=None, provider_output_tokens=None)
            journal.fail_call(call["call_id"], code="d-transport-execution-unknown")
            write_json_exclusive(folder / "transport-error.json", {"error_type": type(exc).__name__})
            append_row(output_dir / "calls.jsonl", row)
            raise CallBoundary("Unknown execution/cost retained; no replacement call") from exc
        break
    row["duration_ms"] = round((time.monotonic() - start) * 1000)
    (folder / "raw.txt").write_text(reply["raw"], encoding="utf-8")
    row.update(raw_response_path=str(folder / "raw.txt"), raw_response_sha256=_sha(reply["raw"]))
    row["model"] = reply["model"] if isinstance(reply.get("model"), str) and reply["model"] else context["model"]
    for key in ("request_tokens", "output_tokens"):
        value = reply.get(key)
        row[key] = value if type(value) is int and value >= 0 else None
    caller_cut = reply.get("caller_cutoff") is True
    row["usage_kind"] = "caller-cutoff-upper-bound" if caller_cut else "provider-reported"
    row["provider_request_tokens"] = row["request_tokens"]
    row["provider_output_tokens"] = row["output_tokens"]
    if caller_cut:
        # Owner policy: this known active disconnect consumes the full reservation.
        # Never label the conservative charge as provider-measured usage.
        row.update(request_tokens=request_bound, output_tokens=MAX_OUTPUT_TOKENS)
    row["caller_cutoff"] = caller_cut
    if isinstance(reply.get("stream_estimate"), dict):
        row["stream_estimate"] = reply["stream_estimate"]
    if isinstance(reply.get("calibration_check"), dict):
        row["calibration_check"] = reply["calibration_check"]
    request_check = reply.get("request_calibration_check")
    if isinstance(request_check, dict):
        row["request_calibration_check"] = request_check
    usage = None if any(row[key] is None for key in ("request_tokens", "output_tokens")) else row["request_tokens"] + row["output_tokens"]
    if usage is None and journal.budget_policy(context["run_id"]) == "charged-pending":
        row.update(usage_kind="unknown-usage-upper-bound", charged_tokens=call["reservation"])
    evidence = {"binding": binding, "prompt_sha256": row["prompt_sha256"],
        "raw_response_sha256": row["raw_response_sha256"], "request_tokens": row["request_tokens"],
        "output_tokens": row["output_tokens"], "model": row["model"],
        "finish_reason": reply.get("finish_reason"), "measurement_kind": context["measurement_kind"],
        "usage_kind": row["usage_kind"], "caller_cutoff": caller_cut,
        "provider_request_tokens": row["provider_request_tokens"],
        "provider_output_tokens": row["provider_output_tokens"],
        "stream_estimate": row.get("stream_estimate"), "calibration_check": row.get("calibration_check"),
        "request_metering": row.get("request_metering"), "request_calibration_check": request_check}
    write_json_exclusive(folder / "transport.json", evidence)
    recorded = evidence; parse_error = None
    if payload_reader is not None and not caller_cut and reply.get("finish_reason") == "stop":
        try:
            recorded = payload_reader(reply["raw"])
            row["parse_ok"] = True
        except (ValueError, KeyError, TypeError) as exc:
            parse_error = "Review response could not be read: " + str(exc)
    journal.record_response(call_id=call["call_id"], run_id=context["run_id"], task_id=task_id,
        request_token=call["request_token"], payload=recorded,
        event_digest=canonical_digest(evidence), usage_tokens=usage, raw_response=reply["raw"])
    reason = None
    if usage is None:
        reason = "Unknown usage retained; cannot claim bounded measured output or spend again"
    elif row["request_tokens"] > MAX_REQUEST_TOKENS:
        reason = "Observed input exceeds60000; retain usage and stop"
    elif journal.status(context["run_id"])["run"]["state"] != "ACTIVE":
        reason = "Journal deadline or declared budget boundary reached"
    if reason:
        row["diagnostics"] = [reason]
        # Preserve the existing stop across later author/reviewer entry calls.
        # A Python loop-local exception alone cannot stop another role sharing this run.
        if (usage is not None and row["request_tokens"] > MAX_REQUEST_TOKENS
                and journal.review_reservations(context["run_id"])
                and journal.status(context["run_id"])["run"]["state"] == "ACTIVE"):
            journal.stop_authors(context["run_id"], reason=reason)
        else:
            with journal._tx():
                journal._terminalize_active_run(context["run_id"],
                    state="AMBIGUOUS" if usage is None else "BUDGET_OVERRUN",
                    reason="bounded-call-stop", detail={"call_id":call["call_id"], "diagnostic":reason})
        journal.settle(call["call_id"]); append_row(output_dir / "calls.jsonl", row)
        raise CallBoundary(reason)
    rejected = parse_error
    if caller_cut or row["output_tokens"] > MAX_OUTPUT_TOKENS or reply.get("finish_reason") != "stop":
        rejected = "Section output limited or incomplete; simplify within the same section repair allowance"
    if rejected:
        row["diagnostics"] = [rejected]
        if row.get("repair_limit") == row["attempt"]:
            row["outcome"] = "degraded-T2"
        journal.settle(call["call_id"]); append_row(output_dir / "calls.jsonl", row)
        raise SectionRejected(rejected)
    return call, reply, version

