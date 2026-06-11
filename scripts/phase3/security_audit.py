#!/usr/bin/env python3
"""
Generate a structural Phase-3 security audit report from current run evidence.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import re
from pathlib import Path
from typing import Any

from common.output_language import localize_phase3_security_audit_report, resolve_output_locale
from phase3.surface_policy import write_phase3_profiled_surface


PLACEHOLDER_PATTERNS = (
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r'throw new Error\("Implement [^"]+"\)', re.IGNORECASE),
)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def text_contains(path: Path, pattern: str) -> bool:
    if not path.exists():
        return False
    return pattern in path.read_text(encoding="utf-8")


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def contains_placeholder_content(text: str) -> bool:
    sanitized = re.sub(r"\bplaceholder\s*=\s*(\{[^}]*\}|\"[^\"]*\"|'[^']*')", "", text)
    return any(pattern.search(sanitized) for pattern in PLACEHOLDER_PATTERNS)


def list_test_paths(output_dir: Path) -> list[Path]:
    tests_root = output_dir / "tests"
    if not tests_root.exists():
        return []
    return sorted(tests_root.rglob("*.test.ts"))


def matching_test_paths(output_dir: Path, keywords: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for path in list_test_paths(output_dir):
        relative = str(path.relative_to(output_dir))
        content = read_text_if_exists(path)
        haystack = f"{relative}\n{content}".lower()
        if not any(keyword in haystack for keyword in keywords):
            continue
        if contains_placeholder_content(content):
            continue
        if not any(token in content for token in ('describe(', 'it(', 'expect(')):
            continue
        matches.append(relative)
    return sorted(matches)


def matching_source_paths(output_dir: Path, keywords: tuple[str, ...]) -> list[str]:
    source_root = output_dir / "apps" / "api" / "src"
    if not source_root.exists():
        return []
    matches: list[str] = []
    for path in source_root.rglob("*.ts"):
        relative = str(path.relative_to(output_dir))
        content = read_text_if_exists(path)
        haystack = f"{relative}\n{content}".lower()
        if not any(keyword in haystack for keyword in keywords):
            continue
        if contains_placeholder_content(content):
            continue
        matches.append(relative)
    return sorted(matches)


def extract_preferred_vendor(tech_stack_text: str) -> str:
    match = re.search(r'preferred_vendor_class:\s*"([^"]+)"', tech_stack_text)
    return match.group(1).strip() if match else ""


def extract_identity_field(tech_stack_text: str, key: str) -> str:
    match = re.search(rf'{re.escape(key)}:\s*"([^"]+)"', tech_stack_text)
    return match.group(1).strip() if match else ""


def explicit_external_auth_requirement(engineering_spec_text: str) -> bool:
    normalized = engineering_spec_text.lower()
    patterns = (
        r"\b(use|must use|require|requires|required|selected|chosen)\b[^.\n]{0,80}\b(oidc|oauth2|openid)\b",
        r"\b(oidc|oauth2|openid)\b[^.\n]{0,80}\b(provider|idp|identity provider)\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def package_dependency_names(output_dir: Path) -> set[str]:
    dependency_names: set[str] = set()
    for package_path in (
        output_dir / "package.json",
        output_dir / "apps" / "api" / "package.json",
        output_dir / "apps" / "web" / "package.json",
    ):
        payload = load_json_if_exists(package_path)
        if not payload:
            continue
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            deps = payload.get(key, {})
            if isinstance(deps, dict):
                dependency_names.update(str(name).strip() for name in deps.keys() if str(name).strip())
    return dependency_names


def load_phase2_engineering_spec(output_dir: Path) -> str:
    metadata = load_json_if_exists(output_dir / "phase3-run-metadata.json") or {}
    phase2_root = Path(str(metadata.get("phase2_root") or "")).resolve() if metadata.get("phase2_root") else None
    if not phase2_root or not phase2_root.exists():
        return ""
    return read_text_if_exists(phase2_root / "engineering-spec-pack.md")


def declared_auth_posture(*, tech_stack_text: str, engineering_spec_text: str) -> dict[str, Any]:
    contract_source = extract_identity_field(tech_stack_text, "contract_source")
    integration_mode = extract_identity_field(tech_stack_text, "integration_mode")
    external_identity_contract_required = bool(
        integration_mode == "external-idp" or explicit_external_auth_requirement(engineering_spec_text)
    )
    return {
        "preferred_vendor": extract_preferred_vendor(tech_stack_text),
        "contract_source": contract_source,
        "integration_mode": integration_mode,
        "expects_oidc_or_oauth2": external_identity_contract_required,
        "external_identity_contract_required": external_identity_contract_required,
    }


def implemented_auth_posture(output_dir: Path, auth_sources: list[str]) -> dict[str, Any]:
    dependency_names = package_dependency_names(output_dir)
    auth_text = "\n".join(read_text_if_exists(output_dir / path) for path in auth_sources)
    real_external_auth_library_present = any(
        dependency in dependency_names
        for dependency in (
            "openid-client",
            "jose",
            "passport",
            "passport-openidconnect",
            "express-openid-connect",
            "@auth0/nextjs-auth0",
            "next-auth",
        )
    )
    real_auth_library_present = real_external_auth_library_present or any(
        dependency in dependency_names
        for dependency in (
            "express-session",
            "cookie-session",
            "cookie-parser",
            "iron-session",
            "lucia",
            "better-auth",
            "jsonwebtoken",
            "passport-jwt",
            "passport-local",
            "bcrypt",
            "bcryptjs",
            "argon2",
        )
    )
    custom_header_auth_substitution_detected = "x-phase3-auth-context" in auth_text or bool(
        re.search(r'headers?\s*\[\s*["\']x-[^"\']+["\']\s*\]', auth_text, flags=re.IGNORECASE)
    )
    custom_header_auth_context_guarded = bool(
        custom_header_auth_substitution_detected
        and "PHASE3_ALLOW_AUTH_CONTEXT_HEADER" in auth_text
        and re.search(r"PHASE3_ALLOW_AUTH_CONTEXT_HEADER\s*===\s*[\"']true[\"']", auth_text)
    )
    bearer_or_session_signal_present = any(
        token in auth_text.lower() for token in ("authorization", "bearer ", "set-cookie", "session", "openid", "oidc")
    )
    return {
        "real_auth_library_present": real_auth_library_present,
        "real_external_auth_library_present": real_external_auth_library_present,
        "custom_header_auth_substitution_detected": custom_header_auth_substitution_detected,
        "custom_header_auth_context_guarded": custom_header_auth_context_guarded,
        "bearer_or_session_signal_present": bearer_or_session_signal_present,
    }


def analyze_phase3_security(
    *,
    output_dir: Path,
    tech_stack_text: str = "",
) -> dict[str, Any]:
    env_example_path = output_dir / ".env.example"
    errors_path = output_dir / "apps" / "api" / "src" / "common" / "errors.ts"
    tenant_tests = matching_test_paths(output_dir, ("tenant", "cross-tenant"))
    audit_tests = matching_test_paths(output_dir, ("audit", "audit-log"))
    auth_sources = matching_source_paths(output_dir, ("auth", "oidc", "session", "rbac"))
    errors_text = read_text_if_exists(errors_path)
    engineering_spec_text = load_phase2_engineering_spec(output_dir)
    declared_auth = declared_auth_posture(
        tech_stack_text=tech_stack_text,
        engineering_spec_text=engineering_spec_text,
    )
    implemented_auth = implemented_auth_posture(output_dir, auth_sources)
    controlled_test_auth_context_channel = bool(
        implemented_auth["custom_header_auth_substitution_detected"]
        and implemented_auth["custom_header_auth_context_guarded"]
        and implemented_auth["real_auth_library_present"]
    )
    auth_downgrade_detected = bool(
        declared_auth["external_identity_contract_required"]
        and implemented_auth["custom_header_auth_substitution_detected"]
        and not controlled_test_auth_context_channel
        and not implemented_auth["real_external_auth_library_present"]
    )
    header_stub_only_detected = bool(
        implemented_auth["custom_header_auth_substitution_detected"]
        and not controlled_test_auth_context_channel
        and not implemented_auth["real_auth_library_present"]
    )

    checks = {
        "auth_vendor_selected": bool(extract_preferred_vendor(tech_stack_text)),
        "declared_oidc_or_oauth2": bool(declared_auth["expects_oidc_or_oauth2"]),
        "external_auth_contract_required": bool(declared_auth["external_identity_contract_required"]),
        "auth_contract_source": declared_auth["contract_source"],
        "auth_integration_mode": declared_auth["integration_mode"],
        "real_auth_library_present": bool(implemented_auth["real_auth_library_present"]),
        "real_external_auth_library_present": bool(implemented_auth["real_external_auth_library_present"]),
        "custom_header_auth_substitution_detected": bool(implemented_auth["custom_header_auth_substitution_detected"]),
        "custom_header_auth_context_guarded": bool(implemented_auth["custom_header_auth_context_guarded"]),
        "controlled_test_auth_context_channel": controlled_test_auth_context_channel,
        "header_stub_only_detected": header_stub_only_detected,
        "auth_downgrade_detected": auth_downgrade_detected,
        "oidc_secret_placeholder_present": text_contains(env_example_path, "OIDC_CLIENT_SECRET="),
        "oidc_issuer_placeholder_present": text_contains(env_example_path, "OIDC_ISSUER_URL="),
        "oidc_client_id_placeholder_present": text_contains(env_example_path, "OIDC_CLIENT_ID="),
        "tenant_isolation_verification_present": bool(tenant_tests),
        "audit_surface_present": bool(audit_tests),
        "auth_surface_present": bool(auth_sources),
        "error_envelope_present": all(field in errors_text for field in ("error_kind", "error_code", "retryability")),
    }

    findings: list[dict[str, str]] = []
    if checks["external_auth_contract_required"] and not checks["auth_vendor_selected"]:
        findings.append(
            {
                "severity": "critical",
                "title": "Auth vendor posture is not frozen into the Phase-3 stack decision",
                "evidence": "preferred_vendor_class missing",
            }
        )
    if not checks["tenant_isolation_verification_present"]:
        findings.append(
            {
                "severity": "critical",
                "title": "No meaningful tenant isolation verification surface was found",
                "evidence": "tenant/cross-tenant tests missing or still placeholder",
            }
        )
    if not checks["auth_surface_present"]:
        findings.append(
            {
                "severity": "critical",
                "title": "No meaningful auth/session enforcement surface was found in the backend implementation",
                "evidence": "auth/session/oidc/rbac source surface missing or still placeholder",
            }
        )
    if checks["header_stub_only_detected"]:
        findings.append(
            {
                "severity": "critical",
                "title": "Auth enforcement still relies on custom header context without real credential or session validation",
                "evidence": "custom header auth context detected without a real auth/session library",
            }
        )
    if checks["declared_oidc_or_oauth2"] and checks["auth_downgrade_detected"]:
        findings.append(
            {
                "severity": "critical",
                "title": "Auth implementation downgrade detected",
                "evidence": "declared external IdP / OIDC posture was reduced to custom header parsing without a real external auth library",
            }
        )
    if not checks["error_envelope_present"]:
        findings.append(
            {
                "severity": "critical",
                "title": "API error envelope surface is missing required structured fields",
                "evidence": str(errors_path.relative_to(output_dir)) if errors_path.exists() else "errors.ts missing",
            }
        )
    if checks["external_auth_contract_required"] and not checks["oidc_secret_placeholder_present"]:
        findings.append(
            {
                "severity": "high",
                "title": "OIDC secret placeholder is missing from the runtime env template",
                "evidence": str(env_example_path.relative_to(output_dir)) if env_example_path.exists() else ".env.example missing",
            }
        )
    if checks["external_auth_contract_required"] and (
        not checks["oidc_issuer_placeholder_present"] or not checks["oidc_client_id_placeholder_present"]
    ):
        findings.append(
            {
                "severity": "high",
                "title": "OIDC runtime env placeholders are incomplete for the declared auth posture",
                "evidence": str(env_example_path.relative_to(output_dir)) if env_example_path.exists() else ".env.example missing",
            }
        )
    if not checks["audit_surface_present"]:
        findings.append(
            {
                "severity": "high",
                "title": "Audit surface verification is missing or still placeholder",
                "evidence": "audit-related tests missing or still placeholder",
            }
        )

    report = {
        "summary": {
            "critical_findings": sum(1 for row in findings if row["severity"] == "critical"),
            "high_findings": sum(1 for row in findings if row["severity"] == "high"),
            "medium_findings": sum(1 for row in findings if row["severity"] == "medium"),
            "low_findings": sum(1 for row in findings if row["severity"] == "low"),
            "checked_test_surface_count": len(list_test_paths(output_dir)),
            "preferred_auth_vendor": extract_preferred_vendor(tech_stack_text),
            "auth_downgrade_findings": 1 if auth_downgrade_detected else 0,
        },
        "checks": checks,
        "evidence": {
            "tenant_tests": tenant_tests,
            "audit_tests": audit_tests,
            "auth_sources": auth_sources,
            "declared_auth": declared_auth,
            "implemented_auth": implemented_auth,
        },
        "findings": findings,
    }
    return report


def build_report_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    checks = report.get("checks", {})
    findings = report.get("findings", [])
    lines = [
        "# Phase-3 Security Audit Report",
        "",
        "## Summary",
        f"- critical_findings: {report['summary']['critical_findings']}",
        f"- high_findings: {report['summary']['high_findings']}",
        f"- preferred_auth_vendor: {report['summary']['preferred_auth_vendor'] or 'not-defined'}",
        "",
        "## Checks",
        f"- auth_vendor_selected: {checks.get('auth_vendor_selected', False)}",
        f"- declared_oidc_or_oauth2: {checks.get('declared_oidc_or_oauth2', False)}",
        f"- external_auth_contract_required: {checks.get('external_auth_contract_required', False)}",
        f"- auth_contract_source: {checks.get('auth_contract_source', '') or 'not-defined'}",
        f"- auth_integration_mode: {checks.get('auth_integration_mode', '') or 'not-defined'}",
        f"- real_auth_library_present: {checks.get('real_auth_library_present', False)}",
        f"- real_external_auth_library_present: {checks.get('real_external_auth_library_present', False)}",
        f"- custom_header_auth_substitution_detected: {checks.get('custom_header_auth_substitution_detected', False)}",
        f"- custom_header_auth_context_guarded: {checks.get('custom_header_auth_context_guarded', False)}",
        f"- controlled_test_auth_context_channel: {checks.get('controlled_test_auth_context_channel', False)}",
        f"- header_stub_only_detected: {checks.get('header_stub_only_detected', False)}",
        f"- auth_downgrade_detected: {checks.get('auth_downgrade_detected', False)}",
        f"- oidc_secret_placeholder_present: {checks.get('oidc_secret_placeholder_present', False)}",
        f"- oidc_issuer_placeholder_present: {checks.get('oidc_issuer_placeholder_present', False)}",
        f"- oidc_client_id_placeholder_present: {checks.get('oidc_client_id_placeholder_present', False)}",
        f"- tenant_isolation_verification_present: {checks.get('tenant_isolation_verification_present', False)}",
        f"- audit_surface_present: {checks.get('audit_surface_present', False)}",
        f"- auth_surface_present: {checks.get('auth_surface_present', False)}",
        f"- error_envelope_present: {checks.get('error_envelope_present', False)}",
        "",
        "## Findings",
    ]
    if not findings:
        lines.append("- none")
    else:
        for finding in findings:
            lines.append(f"- [{finding['severity']}] {finding['title']} ({finding['evidence']})")
    lines.append("")
    return localize_phase3_security_audit_report("\n".join(lines), output_locale)


def run_phase3_security_audit(
    *,
    output_dir: Path,
    tech_stack_text: str = "",
    output_locale: str | None = None,
) -> dict[str, Any]:
    report = analyze_phase3_security(output_dir=output_dir, tech_stack_text=tech_stack_text)
    json_path = output_dir / "security-audit-checklist.json"
    md_path = write_phase3_profiled_surface(output_dir, "security-audit-report.md", build_report_markdown(report, output_locale))
    write_text(json_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        **report["summary"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the structural Phase-3 security audit")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--tech-stack-decision")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    return parser


def main() -> int:
    args = build_parser().parse_args()
    tech_stack_text = ""
    if args.tech_stack_decision:
        tech_stack_text = Path(args.tech_stack_decision).resolve().read_text(encoding="utf-8")
    summary = run_phase3_security_audit(
        output_dir=Path(args.output_dir).resolve(),
        tech_stack_text=tech_stack_text,
        output_locale=args.output_locale,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["critical_findings"] == 0 and summary["high_findings"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
