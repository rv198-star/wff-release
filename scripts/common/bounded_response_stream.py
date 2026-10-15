"""Single Responses SSE transport with a caller-owned output limit for D and P3.

An explicitly calibrated endpoint/model counts text delta events times1.02,
plus the existing1024 opaque-reasoning reserve and64 units per output item.
Completed usage checks detect calibration drift; subsequent calls revert to
byte counting on drift. This estimates opaque reasoning, not remote cancellation.
Unknown endpoint/model pairs continue to use the conservative byte method.
"""
from __future__ import annotations

import http.client
import json
import re
from pathlib import Path
import time
import urllib.error
import urllib.request

from common.bounded_model_call import MAX_OUTPUT_TOKENS, TransportError, compact, estimate_request_tokens
from common.semantic_materialization import write_json_exclusive

REASONING_ALLOWANCE = 1024
ITEM_FRAMING_ALLOWANCE = 64


class StreamError(TransportError):
    """HTTP, malformed or prematurely ended stream: execution cost may be unknown."""


class OutputEstimate:
    def __init__(self, *, calibrated=False):
        self.calibrated = calibrated
        self.delta_counts = {"visible": 0, "reasoning": 0}
        self.unstreamed_bytes = {}
        self.parts = {}
        self.items = set()
        self.reported_output = 0
        self.reported_reasoning = 0

    def _part(self, key, text, *, delta=False):
        if not isinstance(text, str):
            raise StreamError("Text event has no string content")
        prior = self.parts.get(key, "")
        if delta:
            self.delta_counts["reasoning" if key[1].startswith("reasoning") else "visible"] += 1
            self.parts[key] = prior + text
        elif text.startswith(prior):
            self.unstreamed_bytes[key] = self.unstreamed_bytes.get(key, 0) + len(text[len(prior):].encode("utf-8"))
            self.parts[key] = text
        elif prior != text:
            raise StreamError("Completed text conflicts with its streamed prefix")

    def observe(self, event):
        kind = event.get("type", "")
        index = event.get("output_index", 0)
        if kind.startswith("response.output_item."):
            self.items.add(index)
        if kind in {"response.output_text.delta", "response.refusal.delta",
                    "response.reasoning_text.delta", "response.reasoning_summary_text.delta",
                    "response.function_call_arguments.delta"}:
            family = kind.removeprefix("response.").removesuffix(".delta")
            subindex = event.get("content_index", event.get("summary_index", 0))
            self._part((index, family, subindex), event.get("delta"), delta=True)
        elif kind in {"response.output_text.done", "response.refusal.done", "response.reasoning_text.done",
                      "response.reasoning_summary_text.done", "response.function_call_arguments.done"}:
            family = kind.removeprefix("response.").removesuffix(".done")
            text_key = "arguments" if family == "function_call_arguments" else "refusal" if family == "refusal" else "text"
            self._part((index, family, event.get("content_index", event.get("summary_index", 0))), event.get(text_key))
        elif kind.endswith(".delta"):
            raise StreamError("Unsupported output delta cannot be counted")
        if kind in {"response.content_part.added", "response.content_part.done",
                    "response.reasoning_summary_part.added", "response.reasoning_summary_part.done"}:
            part = event.get("part") or {}
            family = part.get("type")
            family = "reasoning_summary_text" if family == "summary_text" else family
            if family in {"output_text", "reasoning_text", "reasoning_summary_text", "refusal"}:
                self._part((index, family, event.get("content_index", event.get("summary_index", 0))),
                           part.get("refusal" if family == "refusal" else "text"))
            else:
                raise StreamError("Unsupported content part cannot be counted")
        if kind in {"response.output_item.added", "response.output_item.done"}:
            self._item(index, event.get("item") or {})
        if isinstance(event.get("response"), dict):
            response = event["response"]
            usage = response.get("usage") or {}
            output = usage.get("output_tokens")
            reasoning = (usage.get("output_tokens_details") or {}).get("reasoning_tokens")
            if type(output) is int and output >= 0:
                self.reported_output = max(self.reported_output, output)
            if type(reasoning) is int and reasoning >= 0:
                self.reported_reasoning = max(self.reported_reasoning, reasoning)
            for i, item in enumerate(response.get("output") or []):
                self._item(i, item)

    def _item(self, index, item):
        self.items.add(index)
        kind = item.get("type")
        if kind == "function_call" and item.get("arguments"):
            self._part((index, "function_call_arguments", 0), item["arguments"])
        for group in ("content", "summary"):
            for i, part in enumerate(item.get(group) or []):
                family = part.get("type")
                family = "reasoning_summary_text" if family == "summary_text" else family
                if family in {"output_text", "reasoning_text", "reasoning_summary_text", "refusal"}:
                    self._part((index, family, i), part.get("refusal" if family == "refusal" else "text"))
                elif part:
                    raise StreamError("Unsupported content cannot be counted")

    def report(self):
        visible = sum(len(value.encode("utf-8")) for (_, kind, _), value in self.parts.items()
                      if not kind.startswith("reasoning"))
        reasoning = sum(len(value.encode("utf-8")) for (_, kind, _), value in self.parts.items()
                        if kind.startswith("reasoning"))
        visible_estimate, reasoning_estimate = visible, reasoning
        if self.calibrated:
            visible_estimate = ((self.delta_counts["visible"] * 102 + 99) // 100) + sum(
                size for (_, kind, _), size in self.unstreamed_bytes.items() if not kind.startswith("reasoning"))
            reasoning_estimate = ((self.delta_counts["reasoning"] * 102 + 99) // 100) + sum(
                size for (_, kind, _), size in self.unstreamed_bytes.items() if kind.startswith("reasoning"))
        reserved = max(REASONING_ALLOWANCE, reasoning_estimate, self.reported_reasoning)
        framing = ITEM_FRAMING_ALLOWANCE * len(self.items)
        return {"method": ("calibrated-sse-delta-1.02-plus-reasoning-reserve-v1" if self.calibrated
                           else "utf8-byte-bound-plus-opaque-reasoning-reserve-v1"),
                "visible_delta_events": self.delta_counts["visible"], "reasoning_delta_events": self.delta_counts["reasoning"],
                "visible_token_estimate": visible_estimate,
                "visible_utf8_bytes": visible, "reasoning_utf8_bytes": reasoning,
                "opaque_reasoning_allowance": REASONING_ALLOWANCE,
                "reasoning_estimate": reserved, "item_framing_allowance": framing,
                "provider_reported_output_tokens": self.reported_output,
                "estimated_output_tokens": max(visible_estimate + reserved + framing, self.reported_output),
                "hidden_reasoning_observable": False}

    def compare_usage(self, usage):
        output = usage.get("output_tokens")
        reasoning = (usage.get("output_tokens_details") or {}).get("reasoning_tokens")
        valid = type(output) is int and type(reasoning) is int and 0 <= reasoning <= output
        visible = output - reasoning if valid else None
        delta = self.delta_counts["visible"]
        deviation = (abs(delta - visible) / visible if visible else (0.0 if delta == 0 else None)) if valid else None
        return {"visible_delta_events": delta, "provider_visible_tokens": visible,
                "relative_deviation": deviation, "deviation_limit": 0.03,
                "comparison": "raw delta count versus provider output minus reasoning tokens",
                "fallback_required": deviation is None or deviation > 0.03,
                "reason": "missing-visible-usage" if deviation is None else
                          "delta-token-drift" if deviation > 0.03 else "within-calibration"}

    def raw(self):
        return "".join(value for (_, kind, _), value in sorted(self.parts.items()) if kind == "output_text")


def read_response_stream(response, *, evidence, max_output_tokens=MAX_OUTPUT_TOKENS, deadline=None, calibrated=False):
    """Read one SSE response, closing it on success, caller cutoff or any error.

    Evidence retains received bytes, including the threshold-crossing event;
    output is never repaired or made to look complete after disconnect.
    """
    if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= MAX_OUTPUT_TOKENS:
        raise ValueError("Output cap must be positive and at most8000")
    estimate = OutputEstimate(calibrated=calibrated); data = []; final = None
    try:
        while True:
            if deadline is not None and time.time() >= deadline:
                raise StreamError("Declared wall deadline reached during stream")
            line = response.readline(262145)
            if not line:
                if data:
                    raise StreamError("Stream ended inside an SSE event")
                break
            evidence.write(line); evidence.flush()
            if len(line) > 262144:
                raise StreamError("Unbounded SSE line cannot be counted safely")
            text = line.decode("utf-8").rstrip("\r\n")
            if text.startswith("data:"):
                data.append(text[5:].removeprefix(" "))
                if sum(len(x) for x in data) > 262144:
                    raise StreamError("Unbounded SSE event cannot be counted safely")
            elif not text and data:
                body = "\n".join(data); data = []
                if body == "[DONE]":
                    break
                event = json.loads(body)
                if not isinstance(event, dict):
                    raise StreamError("SSE data must be an event object")
                if event.get("type") in {"error", "response.failed"}:
                    raise StreamError("Provider reported a stream error")
                estimate.observe(event)
                report = estimate.report()
                if event.get("type") in {"response.completed", "response.incomplete"}:
                    final = event.get("response")
                    break
                if report["estimated_output_tokens"] >= max_output_tokens:
                    response.close()
                    return {"raw": estimate.raw(), "request_tokens": None, "output_tokens": None,
                            "finish_reason": "caller_output_limit", "caller_cutoff": True,
                            "stream_estimate": report}
        if not isinstance(final, dict):
            raise StreamError("No final response received")
        usage = final.get("usage") or {}
        measured_output = usage.get("output_tokens")
        at_limit = (measured_output >= max_output_tokens if calibrated and type(measured_output) is int
                    else estimate.report()["estimated_output_tokens"] >= max_output_tokens)
        return {"raw": estimate.raw(), "model": final.get("model"),
                "calibration_check": estimate.compare_usage(usage),
                "request_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
                "reasoning_tokens": (usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
                "finish_reason": ("output_limit" if at_limit
                    else "stop" if final.get("status") == "completed" else final.get("status", "unknown")),
                "caller_cutoff": False, "stream_estimate": estimate.report(), "response": final}
    finally:
        response.close()


class ResponsesTransport:
    """Host-configured endpoint and credentials; exactly one HTTP request per call."""
    def __init__(self, *, endpoint, api_key, model, output_dir, deadline, reasoning_effort="medium", opener=None, calibration=None):
        self.endpoint = endpoint; self.api_key = api_key; self.model = model
        self.output_dir = Path(output_dir); self.deadline = deadline
        self.reasoning_effort = reasoning_effort; self.opener = opener or urllib.request.urlopen
        self.calibration = calibration if isinstance(calibration, dict) else None
        self.calibrated = bool(isinstance(calibration, dict)
            and calibration.get("endpoint") == endpoint and calibration.get("model") == model
            and re.fullmatch(r"[0-9a-f]{64}", str(calibration.get("evidence_sha256", ""))))
        request_profile = (self.calibration or {}).get("request_calibration", {})
        self.request_divisor = float(request_profile.get("divisor", 1.0)) if self.calibrated else 1.0
        if not 0 < self.request_divisor <= 1.4:
            raise ValueError("Request calibration divisor exceeds Owner-approved1.4")
        if self.request_divisor != 1.0 and not re.fullmatch(r"[0-9a-f]{64}", str(request_profile.get("evidence_sha256", ""))):
            raise ValueError("Request calibration needs bound measured evidence")
        self.request_calibration_enabled = bool(self.calibrated and request_profile)
        self.request_samples = 0
        self.count = 0

    def _check_calibration_binding(self):
        if not self.calibration or self.calibration.get("endpoint") != self.endpoint or self.calibration.get("model") != self.model:
            self.calibrated = False

    def estimate_request_tokens(self, prompt):
        self._check_calibration_binding()
        return estimate_request_tokens(prompt, calibrated=self.calibrated,
            request_divisor=self.request_divisor if self.calibrated else 1.0)

    def request_estimate_metadata(self, prompt):
        self._check_calibration_binding()
        return {"conservative_bound": estimate_request_tokens(prompt, calibrated=self.calibrated),
                "estimate": self.estimate_request_tokens(prompt),
                "divisor": self.request_divisor if self.calibrated else 1.0,
                "completed_samples": self.request_samples}

    def _observe_request_usage(self, prompt, reply, before):
        usage = reply.get("request_tokens")
        sampled = bool(self.request_calibration_enabled and self.calibrated
            and reply.get("model") == self.model and reply.get("finish_reason") == "stop"
            and not reply.get("caller_cutoff") and type(usage) is int and usage > 0)
        observed = before["conservative_bound"] / usage if sampled else None
        if sampled:
            self.request_samples += 1
            self.request_divisor = min(self.request_divisor, observed)
        return {**before, "sampled": sampled, "initial_sample": sampled and self.request_samples <= 3, "observed_input_tokens": usage,
                "observed_ratio": observed, "next_divisor": self.request_divisor if self.calibrated else 1.0,
                "completed_samples": self.request_samples}

    def __call__(self, prompt, *, max_output_tokens):
        self._check_calibration_binding()
        if not 0 < max_output_tokens <= MAX_OUTPUT_TOKENS:
            raise ValueError("Output cap must be positive and at most8000")
        remaining = self.deadline - time.time()
        if remaining <= 0:
            raise StreamError("Declared wall deadline reached before HTTP call")
        request_before = self.request_estimate_metadata(prompt)
        self.count += 1
        folder = self.output_dir / f"transport-{self.count:02d}"; folder.mkdir(parents=True, exist_ok=False)
        body = {"model": self.model, "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                "max_output_tokens": max_output_tokens, "reasoning": {"effort": self.reasoning_effort},
                "tools": [], "stream": True, "store": False}
        write_json_exclusive(folder / "request.json", body)
        key = self.api_key()
        request = urllib.request.Request(self.endpoint, data=compact(body).encode("utf-8"),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept": "text/event-stream"}, method="POST")
        try:
            response = self.opener(request, timeout=min(480, remaining))
            with (folder / "events.sse").open("xb") as evidence:
                reply = read_response_stream(response, evidence=evidence, max_output_tokens=max_output_tokens, deadline=self.deadline, calibrated=self.calibrated)
        except urllib.error.HTTPError as exc:
            write_json_exclusive(folder / "http-error.json", {"status": exc.code})
            exc.close()
            raise StreamError("HTTP request failed with status " + str(exc.code)) from None
        except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.HTTPException,
                UnicodeError, json.JSONDecodeError) as exc:
            write_json_exclusive(folder / "stream-error.json", {"error_type": type(exc).__name__})
            raise StreamError("HTTP/stream transport failed: " + type(exc).__name__) from None
        check = reply.get("calibration_check")
        if isinstance(check, dict):
            check["calibrated_before_call"] = self.calibrated
            check["evidence_sha256"] = self.calibration.get("evidence_sha256") if self.calibration else None
            if reply.get("model") != self.model:
                check.update(fallback_required=True, reason="response-model-changed-recalibration-required")
            if check["fallback_required"]:
                self.calibrated = False
            check["next_call_method"] = "calibrated-delta" if self.calibrated else "utf8-bytes"
            write_json_exclusive(folder / "calibration-check.json", check)
        request_check = self._observe_request_usage(prompt, reply, request_before)
        reply["request_calibration_check"] = request_check
        write_json_exclusive(folder / "request-calibration-check.json", request_check)
        if "response" in reply:
            write_json_exclusive(folder / "response.json", reply.pop("response"))
        reply["model"] = reply.get("model") or self.model
        write_json_exclusive(folder / "stream-result.json", reply)
        return reply
