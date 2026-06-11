#!/usr/bin/env python3
"""Phase-2 first-version runtime slice: phase2_first_version_runtime.py."""

from __future__ import annotations

from phase2.phase2_first_version_stage_renderers import *  # noqa: F401,F403

def emit_phase2_first_version_claim_control_sidecars(
    *,
    output_dir: Path,
    phase1_prd: Path,
    artifact_paths: list[Path],
) -> dict[str, Any]:
    claims, source_mode, upstream_sidecar = _phase1_claims_for_phase2(phase1_prd)
    accepted_phase1_claim_ids = {claim.id for claim in claims}
    results = []
    for artifact_path in artifact_paths:
        if not artifact_path.exists():
            continue
        result = emit_path_b_claim_control_sidecar(
            artifact_path=artifact_path,
            artifact_id=f"p2:{artifact_path.stem}",
            claims=claims,
            view_id=f"p2:{artifact_path.stem}",
            source_count=2 if upstream_sidecar else 1,
            upstream_surface_paths=[path for path in [phase1_prd, upstream_sidecar] if path],
        )
        upstream_ref_audit = audit_phase2_artifact_upstream_claim_refs(
            artifact_path,
            accepted_phase1_claim_ids=accepted_phase1_claim_ids,
        )
        acceptance_status = result["acceptance"]["overall_status"]
        artifact_status = (
            "blocked"
            if acceptance_status == "blocked" or upstream_ref_audit["overall_status"] == "blocked"
            else "review_bound"
            if acceptance_status != "pass"
            else "pass"
        )
        classifications = sorted(
            set(result["acceptance"].get("classifications", []) + upstream_ref_audit["classifications"])
        )
        results.append(
            {
                "artifact_path": str(artifact_path),
                "sidecar_path": result["sidecar_path"],
                "overall_status": artifact_status,
                "claim_control_acceptance_status": acceptance_status,
                "classifications": classifications,
                "claim_count": len(result["surface"]["claim_index"]["claims"]),
                "declared_upstream_p1_claim_refs": upstream_ref_audit["declared_upstream_p1_claim_refs"],
                "unknown_upstream_p1_claim_refs": upstream_ref_audit["unknown_upstream_p1_claim_refs"],
            }
        )
    overall_status = phase2_claim_control_report_status(
        artifact_statuses=[row["overall_status"] for row in results],
        phase1_claim_source_mode=source_mode,
    )
    report = {
        "artifact_kind": "phase2-claim-control-sidecar-report",
        "overall_status": overall_status,
        "claim_ceiling": phase2_claim_control_claim_ceiling(
            overall_status=overall_status,
            phase1_claim_source_mode=source_mode,
        ),
        "phase1_claim_source_mode": source_mode,
        "phase1_claim_control_sidecar": str(upstream_sidecar) if upstream_sidecar else "",
        "artifacts": results,
    }
    report_path = resolve_cross_phase_surface_path(output_dir, "phase2", "phase2-claim-control-report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(report_path, json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    return {"report_path": report_path, "report": report}


def build_phase2_closure_runtime_command(
    *,
    repo_root: Path,
    phase1_prd: Path,
    output_dir: Path,
    version: str,
    complexity_profile: str,
    complexity_override_justification: str = "",
    deployment_posture: str,
    deployment_posture_suggested: str,
    deployment_posture_warning_class: str,
    deployment_posture_override_source: str,
    deployment_posture_override_reason: str,
    deployment_posture_added_risks: str,
    owner: str,
    output_locale: str,
    thinking_value_gain_mode: str = "off",
    thinking_value_gain_output_profile: str = "coverage_rich",
    existing_system_architecture_change_intake: Path | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "phase2" / "phase2_closure_runtime.py"),
        "--phase1-prd",
        str(phase1_prd),
        "--output-dir",
        str(output_dir),
        "--version",
        version,
        "--complexity-profile",
        complexity_profile,
        "--deployment-posture",
        deployment_posture,
        "--deployment-posture-suggested",
        deployment_posture_suggested,
        "--deployment-posture-warning-class",
        deployment_posture_warning_class,
        "--deployment-posture-override-source",
        deployment_posture_override_source,
        "--deployment-posture-override-reason",
        deployment_posture_override_reason,
        "--deployment-posture-added-risks",
        deployment_posture_added_risks,
        "--owner",
        owner,
        "--output-locale",
        output_locale,
    ]
    if complexity_override_justification:
        command.extend(
            [
                "--complexity-override-justification",
                complexity_override_justification,
            ]
        )
    if existing_system_architecture_change_intake:
        command.extend(
            [
                "--existing-system-architecture-change-intake",
                str(existing_system_architecture_change_intake),
            ]
        )
    if thinking_value_gain_mode != "off":
        command.extend(["--thinking-value-gain-mode", thinking_value_gain_mode])
        command.extend(["--thinking-value-gain-output-profile", thinking_value_gain_output_profile])
    return command


def build_full_trial_wrapper_command(**kwargs: Any) -> list[str]:
    return build_phase2_closure_runtime_command(**kwargs)


def run_wrapper(
    *,
    repo_root: Path,
    phase1_prd: Path,
    output_dir: Path,
    version: str,
    complexity_profile: str,
    complexity_override_justification: str = "",
    deployment_posture: str,
    deployment_posture_suggested: str,
    deployment_posture_warning_class: str,
    deployment_posture_override_source: str,
    deployment_posture_override_reason: str,
    deployment_posture_added_risks: str,
    owner: str,
    output_locale: str,
    thinking_value_gain_mode: str = "off",
    thinking_value_gain_output_profile: str = "coverage_rich",
    existing_system_architecture_change_intake: Path | None = None,
) -> int:
    command = build_phase2_closure_runtime_command(
        repo_root=repo_root,
        phase1_prd=phase1_prd,
        output_dir=output_dir,
        version=version,
        complexity_profile=complexity_profile,
        complexity_override_justification=complexity_override_justification,
        deployment_posture=deployment_posture,
        deployment_posture_suggested=deployment_posture_suggested,
        deployment_posture_warning_class=deployment_posture_warning_class,
        deployment_posture_override_source=deployment_posture_override_source,
        deployment_posture_override_reason=deployment_posture_override_reason,
        deployment_posture_added_risks=deployment_posture_added_risks,
        owner=owner,
        output_locale=output_locale,
        thinking_value_gain_mode=thinking_value_gain_mode,
        thinking_value_gain_output_profile=thinking_value_gain_output_profile,
        existing_system_architecture_change_intake=existing_system_architecture_change_intake,
    )
    proc = subprocess.run(command, text=True, capture_output=True, check=False)
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0 and proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode


def build_phase2_first_version_context(args: argparse.Namespace) -> Phase2FirstVersionContext:
    repo_root = Path(__file__).resolve().parents[2]
    phase1_prd = Path(args.phase1_prd).resolve()
    existing_system_architecture_change_intake = resolve_existing_system_architecture_change_intake(
        str(getattr(args, "existing_system_architecture_change_intake", "") or "")
    )
    output_dir = Path(args.output_dir).resolve()
    phase1_prototype_spec = _resolve_phase1_prototype_asset_path(
        phase1_prd,
        candidate_names=("prototype-spec.md", "prototype_spec.md"),
    )
    phase1_prototype_prompt_pack = _resolve_phase1_prototype_asset_path(
        phase1_prd,
        candidate_names=("prototype-prompt-pack.md", "prototype_prompt_pack.md"),
    )
    phase1_interaction_flow_contract = _resolve_phase1_interaction_flow_contract_path(phase1_prd)
    case_name = args.case_name or infer_case_name(output_dir)
    complexity_profile, complexity_report = derive_complexity_profile(args, phase1_prd)
    ensure_output_dir(output_dir, bool(args.force))
    return Phase2FirstVersionContext(
        repo_root=repo_root,
        phase1_prd=phase1_prd,
        existing_system_architecture_change_intake=existing_system_architecture_change_intake,
        output_dir=output_dir,
        phase1_prototype_spec=phase1_prototype_spec,
        phase1_prototype_prompt_pack=phase1_prototype_prompt_pack,
        phase1_interaction_flow_contract=phase1_interaction_flow_contract,
        case_name=case_name,
        version=str(args.version),
        complexity_profile=complexity_profile,
        complexity_override_justification=str(getattr(args, "complexity_override_justification", "") or ""),
        complexity_report=complexity_report,
        deployment_posture=str(args.deployment_posture),
        deployment_posture_suggested=str(args.deployment_posture_suggested),
        deployment_posture_warning_class=str(args.deployment_posture_warning_class),
        deployment_posture_override_source=str(args.deployment_posture_override_source),
        deployment_posture_override_reason=str(args.deployment_posture_override_reason),
        deployment_posture_added_risks=str(args.deployment_posture_added_risks),
        pure_prd_direct=bool(args.pure_prd_direct or True),
        owner=str(args.owner),
        output_locale=resolve_output_locale(args.output_locale),
        thinking_value_gain_mode=str(getattr(args, "thinking_value_gain_mode", "off") or "off"),
        thinking_value_gain_output_profile=str(
            getattr(args, "thinking_value_gain_output_profile", "coverage_rich") or "coverage_rich"
        ),
        run_wrapper=bool(args.run_wrapper),
        force=bool(args.force),
    )


def run_phase2_first_version(context: Phase2FirstVersionContext) -> Phase2FirstVersionResult:
    timing_started_at = utc_now_iso()
    timing_started_monotonic = time.monotonic()
    timing_segments: list[dict[str, object]] = []
    timing_report_path = resolve_cross_phase_surface_path(context.output_dir, "phase2", "phase2-timing-report.json")
    try:
        phase1_page_map = phase2_timed_segment(
            timing_segments,
            "extract_prototype_page_map",
            lambda: _extract_page_map_from_prototype_spec(context.phase1_prototype_spec),
        )
        parsed_phase1_context = phase2_timed_segment(
            timing_segments,
            "parse_phase1_context",
            lambda: parse_phase1_context(
                context.phase1_prd,
                context.case_name,
                context.complexity_profile,
                prototype_pages=phase1_page_map,
            ),
        )

        def detect_integrations() -> tuple[int, list[str]]:
            text = str(parsed_phase1_context["text"])
            return count_external_integrations(text), detect_external_integration_categories(text)

        external_integration_count, external_integration_categories = phase2_timed_segment(
            timing_segments,
            "detect_external_integrations",
            detect_integrations,
        )
        with_stage_02_5 = external_integration_count > 0
        services = phase2_timed_segment(
            timing_segments,
            "build_service_specs",
            lambda: build_service_specs(parsed_phase1_context, context.complexity_profile),
        )
        table_specs = phase2_timed_segment(
            timing_segments,
            "build_table_specs",
            lambda: build_table_specs(
                parsed_phase1_context,
                str(parsed_phase1_context["root_namespace"]),
                context.complexity_profile,
                services,
            ),
        )
        endpoint_specs = phase2_timed_segment(
            timing_segments,
            "build_stage_03_endpoint_specs",
            lambda: build_stage_03_endpoint_specs(
                services,
                root_namespace=str(parsed_phase1_context["root_namespace"]),
                table_specs=table_specs,
            ),
        )
        existing_system_architecture_change_intake = phase2_timed_segment(
            timing_segments,
            "materialize_existing_system_architecture_change_intake",
            lambda: materialize_existing_system_architecture_change_intake(
                source=context.existing_system_architecture_change_intake,
                output_dir=context.output_dir,
            ),
        )
        existing_system_architecture_change_addendum = render_existing_system_architecture_change_addendum(
            intake_path=existing_system_architecture_change_intake,
            relative_to=context.output_dir,
        )

        phase2_timed_segment(
            timing_segments,
            "write_generation_manifest",
            lambda: write_cross_phase_profiled_surface(
                context.output_dir,
                "phase2",
                "phase-2-first-pass-generation-manifest.md",
                build_manifest(
                    case_name=context.case_name,
                    version=context.version,
                    phase1_prd=context.phase1_prd,
                    output_dir=context.output_dir,
                    pure_prd_direct=context.pure_prd_direct,
                    with_stage_02_5=with_stage_02_5,
                ),
            ),
        )

        stage_01 = phase2_timed_segment(
            timing_segments,
            "render_stage_01",
            lambda: render_stage_01(
                case_name=context.case_name,
                phase1_prd=context.phase1_prd,
                complexity_profile=context.complexity_profile,
                context=parsed_phase1_context,
                services=services,
            ),
        )
        if existing_system_architecture_change_addendum:
            stage_01 = stage_01.rstrip() + "\n\n" + existing_system_architecture_change_addendum
        stage_02 = phase2_timed_segment(
            timing_segments,
            "render_stage_02",
            lambda: render_stage_02(
                phase1_prd=context.phase1_prd,
                complexity_profile=context.complexity_profile,
                context=parsed_phase1_context,
                services=services,
                table_specs=table_specs,
            ),
        )
        stage_03 = phase2_timed_segment(
            timing_segments,
            "render_stage_03",
            lambda: render_stage_03(
                phase1_prd=context.phase1_prd,
                phase1_prototype_spec=context.phase1_prototype_spec,
                phase1_interaction_flow_contract=context.phase1_interaction_flow_contract,
                complexity_profile=context.complexity_profile,
                context=parsed_phase1_context,
                services=services,
                endpoint_specs=endpoint_specs,
                table_specs=table_specs,
            ),
        )
        stage_02_5 = ""
        if with_stage_02_5:
            stage_02_5 = phase2_timed_segment(
                timing_segments,
                "render_stage_02_5",
                lambda: render_stage_02_5(
                    phase1_prd=context.phase1_prd,
                    context=parsed_phase1_context,
                    categories=external_integration_categories,
                ),
            )
        stage_04 = phase2_timed_segment(
            timing_segments,
            "render_stage_04",
            lambda: render_stage_04(
                phase1_prd=context.phase1_prd,
                phase1_prototype_spec=context.phase1_prototype_spec,
                phase1_prototype_prompt_pack=context.phase1_prototype_prompt_pack,
                phase1_interaction_flow_contract=context.phase1_interaction_flow_contract,
                complexity_profile=context.complexity_profile,
                context=parsed_phase1_context,
                services=services,
                contract_names=[service.public_contract for service in endpoint_specs],
                endpoint_names=[service.endpoint_name for service in endpoint_specs],
                stage_03_text=stage_03,
                stage_02_5_text=stage_02_5,
            ),
        )
        if existing_system_architecture_change_addendum:
            stage_04 = stage_04.rstrip() + "\n\n" + existing_system_architecture_change_addendum

        def write_stage_artifacts() -> None:
            write_text(context.output_dir / "stage-01-architecture-definition-and-boundary-setting.md", stage_01)
            write_text(context.output_dir / "stage-02-domain-module-service-decomposition.md", stage_02)
            if with_stage_02_5:
                write_text(context.output_dir / "stage-02.5-third-party-integration-architecture-design.md", stage_02_5)
            write_text(context.output_dir / "stage-03-data-storage-and-interface-design.md", stage_03)
            write_text(context.output_dir / "stage-04-design-convergence-and-delivery-prototype.md", stage_04)

        phase2_timed_segment(timing_segments, "write_stage_artifacts", write_stage_artifacts)

        phase2_timed_segment(
            timing_segments,
            "write_generation_sidecars",
            lambda: write_generation_sidecars(
                output_dir=context.output_dir,
                phase1_prd=context.phase1_prd,
                case_name=context.case_name,
                version=context.version,
                complexity_profile=context.complexity_profile,
                complexity_report=context.complexity_report,
                owner=context.owner,
                existing_system_architecture_change_intake=existing_system_architecture_change_intake,
            ),
        )
        claim_control_result = phase2_timed_segment(
            timing_segments,
            "emit_claim_control_sidecars",
            lambda: emit_phase2_first_version_claim_control_sidecars(
                output_dir=context.output_dir,
                phase1_prd=context.phase1_prd,
                artifact_paths=[
                    context.output_dir / "stage-01-architecture-definition-and-boundary-setting.md",
                    context.output_dir / "stage-02-domain-module-service-decomposition.md",
                    context.output_dir / "stage-03-data-storage-and-interface-design.md",
                    context.output_dir / "stage-04-design-convergence-and-delivery-prototype.md",
                ],
            ),
        )
        audit = phase2_timed_segment(
            timing_segments,
            "inspect_case",
            lambda: inspect_case(context.output_dir),
        )
        return Phase2FirstVersionResult(
            audit=audit,
            with_stage_02_5=with_stage_02_5,
            timing_report_path=timing_report_path,
            claim_control_report_path=claim_control_result["report_path"],
        )
    finally:
        write_phase2_timing_report(
            output_dir=context.output_dir,
            started_at=timing_started_at,
            started_monotonic=timing_started_monotonic,
            segments=timing_segments,
        )


def build_phase2_first_version_summary(
    context: Phase2FirstVersionContext,
    result: Phase2FirstVersionResult,
) -> dict[str, object]:
    summary = {
        "output_dir": str(context.output_dir),
        "case_name": context.case_name,
        "version": context.version,
        "complexity_profile": context.complexity_profile,
        "deployment_posture_selected": context.deployment_posture,
        "deployment_posture_suggested": context.deployment_posture_suggested,
        "first_pass_status": result.audit["status"],
        "passed": result.audit["passed"],
        "wrapper_requested": context.run_wrapper,
        "thinking_value_gain_mode": context.thinking_value_gain_mode,
        "thinking_value_gain_output_profile": context.thinking_value_gain_output_profile,
        "stage_02_5_generated": result.with_stage_02_5,
        "timing_report": str(result.timing_report_path),
        "claim_control_report": str(result.claim_control_report_path or ""),
    }
    return summary


def emit_phase2_first_version_summary(summary: dict[str, object]) -> None:
    print(json.dumps(summary, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    args = parse_phase2_first_version_args(argv)
    try:
        context = build_phase2_first_version_context(args)
    except ValueError as exc:
        print(f"[BLOCKED] {exc}")
        return 2
    result = run_phase2_first_version(context)
    emit_phase2_first_version_summary(build_phase2_first_version_summary(context, result))

    if not result.audit["passed"]:
        return 2
    if context.run_wrapper:
        return run_wrapper(
            repo_root=context.repo_root,
            phase1_prd=context.phase1_prd,
            output_dir=context.output_dir,
            version=context.version,
            complexity_profile=context.complexity_profile,
            complexity_override_justification=context.complexity_override_justification,
            deployment_posture=context.deployment_posture,
            deployment_posture_suggested=context.deployment_posture_suggested,
            deployment_posture_warning_class=context.deployment_posture_warning_class,
            deployment_posture_override_source=context.deployment_posture_override_source,
            deployment_posture_override_reason=context.deployment_posture_override_reason,
            deployment_posture_added_risks=context.deployment_posture_added_risks,
            owner=context.owner,
            output_locale=context.output_locale,
            thinking_value_gain_mode=context.thinking_value_gain_mode,
            thinking_value_gain_output_profile=context.thinking_value_gain_output_profile,
            existing_system_architecture_change_intake=context.existing_system_architecture_change_intake,
        )
    emit_review_surface(context.output_dir, "phase2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [name for name in globals() if not name.startswith("__")]
