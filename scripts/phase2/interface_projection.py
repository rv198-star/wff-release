#!/usr/bin/env python3
"""Deterministic Phase-2 interface example and schema projection helpers."""

from __future__ import annotations

from dataclasses import dataclass

from phase2.schema_projection import flatten_schema_fields, unique_preserve
from phase2.technical_naming import choose_technical_pascal, choose_technical_snake


@dataclass(frozen=True)
class ServiceProjectionSpec:
    service_name: str
    domain: str
    home_module: str
    service_type: str
    owns_or_coordinates: str
    primary_inbound: str
    primary_outbound: str
    purpose: str
    public_contract: str
    endpoint_name: str
    method: str
    path: str
    technical_name: str = ""
    technical_slug: str = ""


def service_technical_name(service: ServiceProjectionSpec) -> str:
    return service.technical_name or choose_technical_pascal(service.owns_or_coordinates, prefix="Entity")


def to_snake(raw: str) -> str:
    return choose_technical_snake(raw, prefix="value")


def to_camel(raw: str) -> str:
    pascal = choose_technical_pascal(raw, prefix="Value")
    return pascal[:1].lower() + pascal[1:] if pascal else ""


def infer_collection_alias(endpoint_name: str) -> str:
    normalized = str(endpoint_name or "").strip()
    if normalized.startswith("List"):
        stem = normalized[len("List") :]
        return to_camel(stem) or "items"
    return ""


def semantic_service_key(service: ServiceProjectionSpec) -> str:
    signature = " ".join(
        [
            service.service_name,
            service.domain,
            service.home_module,
            service.owns_or_coordinates,
            service.primary_inbound,
            service.primary_outbound,
            service.purpose,
            service.public_contract,
            service.endpoint_name,
            service.path,
        ]
    ).lower()
    if "access-policy" in signature or ("tenant" in signature and "access" in signature and "policy" in signature):
        return "tenant_access_policy"
    if "trackedscope" in signature or "tracked scope" in signature or "create tracked scope" in signature:
        return "tracked_scope"
    if "attribution" in signature and "seam" in signature:
        return "attribution_seam"
    if "observation" in signature and "run" in signature:
        return "observation_run"
    if "finding" in signature:
        return "finding_query"
    if "recommendation" in signature and "decision" in signature:
        return "recommendation_decision"
    if "optimization task" in signature or "taskbridge" in signature or "task bridge" in signature:
        return "optimization_task"
    if "content asset" in signature:
        return "content_asset"
    if "review" in signature and "report" in signature:
        return "review_report"
    if "audit" in signature:
        return "audit_record"
    return ""


def sample_request_example_value(field_name: str) -> object:
    normalized = str(field_name).strip()
    lowered = normalized.lower()
    if not normalized:
        return "sample-value"
    if normalized in {"tenantId", "tenant_id"}:
        return "tenant-001"
    if lowered.endswith("status") or lowered == "status":
        return "draft"
    if lowered.endswith("decision") or lowered == "decision":
        return "draft"
    if lowered.endswith("version"):
        return 1
    if lowered == "cursor":
        return None
    if lowered in {"pagesize", "page_size", "limit", "count", "qty", "quantity", "stockqty", "petage", "age"}:
        return 25 if "page" in lowered else 1
    if lowered.startswith(("is", "has", "include", "allow", "enable")) or lowered.endswith(("enabled", "required", "visible")):
        return True
    if lowered.endswith(("date", "time", "datetime", "at")) or "date" in lowered or "time" in lowered:
        return "2026-04-10T10:00:00Z"
    if normalized.endswith("Id") or normalized.endswith("ID"):
        return f"{to_snake(normalized[:-2])}-001"
    if lowered.endswith(("amount", "price", "fee", "fees", "score", "percent", "percentage")):
        return 1
    return f"{to_snake(normalized)}-sample"


def set_nested_request_example_path(example: dict[str, object], target_path: str, value: object) -> None:
    segments = [segment.strip() for segment in str(target_path).split(".") if segment.strip()]
    if not segments or segments[0] != "request":
        return
    current: dict[str, object] = example
    for segment in segments[1:-1]:
        nested = current.get(segment)
        if not isinstance(nested, dict):
            nested = {}
            current[segment] = nested
        current = nested
    leaf = segments[-1]
    if leaf not in current:
        current[leaf] = value


def enrich_request_example_with_request_mappings(
    example: dict[str, object],
    service: ServiceProjectionSpec,
    request_mapping_lookup: dict[tuple[str, str], list[str]] | None = None,
) -> dict[str, object]:
    if not request_mapping_lookup:
        return example
    enriched = dict(example)
    for mapping_text in request_mapping_lookup.get((service.path, service.method.upper()), []):
        for raw_entry in mapping_text.split(";"):
            entry = raw_entry.strip()
            if not entry or "->" not in entry:
                continue
            alias, target = [part.strip() for part in entry.split("->", 1)]
            if not target.startswith("request."):
                continue
            sample_value = sample_request_example_value(alias.split(".")[-1])
            set_nested_request_example_path(enriched, target, sample_value)
    return enriched


def request_example(
    service: ServiceProjectionSpec,
    request_mapping_lookup: dict[tuple[str, str], list[str]] | None = None,
) -> dict[str, object]:
    semantic_key = semantic_service_key(service)
    if semantic_key == "tenant_access_policy":
        example = {"tenantId": "tenant-001"}
    elif semantic_key == "tracked_scope":
        example = {"tenantId": "tenant-001", "scopeKey": "brand-core", "brandName": "Acme"}
    elif semantic_key == "observation_run":
        example = {"tenantId": "tenant-001", "scopeId": "scope-001", "runMode": "baseline"}
    elif semantic_key == "finding_query":
        if service.endpoint_name.startswith("List"):
            example = {
                "tenantId": "tenant-001",
                "observationRunId": "run-001",
                "priorityBands": ["high", "medium"],
                "includeCompetitorWindow": True,
                "cursor": None,
                "pageSize": 25,
            }
        else:
            example = {"tenantId": "tenant-001", "findingId": "finding-001"}
    elif semantic_key == "recommendation_decision":
        example = {
            "tenantId": "tenant-001",
            "findingId": "finding-001",
            "assetId": "asset-001",
            "decision": "draft",
            "payloadVersion": "v1",
        }
    elif semantic_key == "optimization_task":
        if service.endpoint_name.startswith("List"):
            example = {"tenantId": "tenant-001", "status": "open", "cursor": None, "pageSize": 25}
        else:
            example = {"tenantId": "tenant-001", "recommendationId": "recommendation-001", "status": "open"}
    elif semantic_key == "review_report":
        example = {
            "tenantId": "tenant-001",
            "scopeId": "scope-001",
            "cycleKey": "2026-W15",
            "freezeTaskStatusesBefore": "submitted",
            "includeUncertaintyBreakdown": True,
        }
    elif semantic_key == "attribution_seam":
        example = {"tenantId": "tenant-001", "scopeId": "scope-001"}
    else:
        entity_key = f"{to_camel(service_technical_name(service))}Id" or "entityId"
        example = {"tenantId": "tenant-001", entity_key: f"{to_snake(service_technical_name(service))}-001"}
        if service.endpoint_name.startswith("List"):
            example["status"] = "active"
            example["cursor"] = None
            example["pageSize"] = 25
        elif service.method == "PATCH" or "Update" in service.endpoint_name:
            example["status"] = "updated"
            example["expectedVersion"] = 2
        elif service.method == "POST":
            example["status"] = "draft"
            example["input"] = {"summary": f"{service.owns_or_coordinates} workflow input"}
    return enrich_request_example_with_request_mappings(example, service, request_mapping_lookup)


def response_example(service: ServiceProjectionSpec) -> dict[str, object]:
    semantic_key = semantic_service_key(service)
    if semantic_key == "tenant_access_policy":
        return {"data": {"tenantId": "tenant-001", "role": "growth_owner", "policyDecision": "allow"}, "meta": {"traceId": "trace-001"}}
    if semantic_key == "tracked_scope":
        return {"data": {"scopeId": "scope-001", "status": "active", "activeRevisionNo": 1}, "meta": {"traceId": "trace-001"}}
    if semantic_key == "observation_run":
        return {"data": {"observationRunId": "run-001", "status": "queued", "measurementWindow": "last-7d"}, "meta": {"traceId": "trace-001"}}
    if semantic_key == "finding_query":
        if service.endpoint_name.startswith("List"):
            return {
                "data": {
                    "findings": [
                        {
                            "findingId": "finding-001",
                            "scopeId": "scope-001",
                            "severity": "high",
                            "score": "0.82",
                            "priorityBand": "high",
                            "measurementWindow": "last-7d",
                            "recommendationStatus": "draft",
                            "traceAnchor": "trace-001",
                        }
                    ]
                },
                "meta": {"traceId": "trace-001", "nextCursor": "cursor-001", "readModelVersion": 1},
            }
        return {"data": {"findingId": "finding-001", "scopeId": "scope-001", "severity": "high", "score": "0.82", "traceAnchor": "trace-001"}, "meta": {"traceId": "trace-001"}}
    if semantic_key == "recommendation_decision":
        return {"data": {"recommendationId": "recommendation-001", "findingId": "finding-001", "payloadVersion": "v1", "decisionStatus": "draft"}, "meta": {"traceId": "trace-001"}}
    if semantic_key == "optimization_task":
        if service.endpoint_name.startswith("List"):
            return {"data": {"optimizationTasks": [{"taskId": "task-001", "recommendationId": "recommendation-001", "status": "open", "dueAt": "2026-04-15"}]}, "meta": {"traceId": "trace-001", "nextCursor": "cursor-001"}}
        return {"data": {"taskId": "task-001", "recommendationId": "recommendation-001", "status": "open"}, "meta": {"traceId": "trace-001"}}
    if semantic_key == "review_report":
        return {
            "data": {
                "reviewReportId": "review-001",
                "status": "generated",
                "uncertaintyLevel": "medium",
                "uncertaintyNote": "sample still small",
                "decisionPosture": "revise",
                "thresholdRationale": "repeatability remains below threshold",
                "reviewSummary": {"executedTaskCount": 3, "acceptedRecommendationCount": 2, "blockedTaskCount": 1},
            },
            "meta": {"traceId": "trace-001"},
        }
    if semantic_key == "attribution_seam":
        return {"data": {"scopeId": "scope-001", "attributionMode": "review-bound", "seamStatus": "reserved"}, "meta": {"traceId": "trace-001"}}
    entity_key = f"{to_camel(service_technical_name(service))}Id" or "entityId"
    item = {entity_key: f"{to_snake(service_technical_name(service))}-001", "status": "active", "module": service.domain}
    if service.endpoint_name.startswith("List"):
        return {"data": [item], "meta": {"traceId": "trace-001", "nextCursor": "cursor-001"}}
    return {"data": item, "meta": {"traceId": "trace-001"}}


def contract_schema_fields(
    service: ServiceProjectionSpec,
    request_mapping_lookup: dict[tuple[str, str], list[str]] | None = None,
) -> list[str]:
    request = request_example(service, request_mapping_lookup=request_mapping_lookup)
    response = response_example(service)
    data = response.get("data")
    meta = response.get("meta")
    collection_alias = infer_collection_alias(service.endpoint_name)
    fields = flatten_schema_fields(request, prefix="request")
    if isinstance(data, list) and collection_alias:
        fields.extend(flatten_schema_fields(data, prefix=f"response.data.{collection_alias}"))
    else:
        fields.extend(flatten_schema_fields(data, prefix="response.data"))
    if isinstance(meta, dict):
        fields.extend(flatten_schema_fields(meta, prefix="response.meta"))
    fields.extend(
        [
            "response.error.error_type: business_error|system_error",
            "response.error.error_code: string",
            "response.error.retryability: string",
            "response.error.caller_action: string",
        ]
    )
    array_object_prefixes = {field.split(": ", 1)[0] for field in fields if field.endswith(": array<object>")}
    if array_object_prefixes:
        fields = [
            field
            for field in fields
            if not any(
                field == f"{prefix}: array<object>" and any(other.startswith(f"{prefix}[].") for other in fields)
                for prefix in array_object_prefixes
            )
        ]
    fields = unique_preserve(fields)
    if fields:
        return fields
    fallback_id = f"{to_snake(service_technical_name(service))}Id"
    return [f"request.{fallback_id}: string", "request.tenantId: string", "response.data.status: string"]
