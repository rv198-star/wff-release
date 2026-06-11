#!/usr/bin/env python3
"""
Audit the Phase-1 skill/runtime family against the current repo structure.

Focus:
- required stage runtime-pack completeness
- runtime symmetry of stage-skill asset ingestion
- convergence-layer runtime presence
- one-click regression/runtime-report presence
- Stage-02b self-test and robustness coverage
- critical PRD section presence for a real trial output
- key documentation alignment for the Stage-02a / Stage-02b split
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import re
from pathlib import Path


STAGE_PACKS = {
    "stage_01": {
        "dir": "reference-packages/phase1-product-requirements/stage-01-user-research",
        "required_runtime_files": (
            "skill-contract.md",
            "stage-sop.md",
            "output-template.md",
            "source-cards.md",
        ),
    },
    "stage_02a": {
        "dir": "reference-packages/phase1-product-requirements/stage-02-requirements-analysis",
        "required_runtime_files": (
            "skill-contract.md",
            "stage-sop.md",
            "output-template.md",
            "source-cards.md",
        ),
    },
    "stage_02b": {
        "dir": "reference-packages/phase1-product-requirements/stage-02b-requirements-specification",
        "required_runtime_files": (
            "skill-contract.md",
            "stage-sop.md",
            "output-template.md",
            "source-cards.md",
        ),
    },
    "stage_03": {
        "dir": "reference-packages/phase1-product-requirements/stage-03-requirements-decomposition",
        "required_runtime_files": (
            "skill-contract.md",
            "stage-sop.md",
            "output-template.md",
            "source-cards.md",
        ),
    },
    "stage_04": {
        "dir": "reference-packages/phase1-product-requirements/stage-04-requirements-validation",
        "required_runtime_files": (
            "skill-contract.md",
            "stage-sop.md",
            "output-template.md",
            "source-cards.md",
        ),
    },
}

DOC_EXPECTATIONS = (
    (
        "examples README acknowledges Stage-02a / Stage-02b structure",
        "reference-packages/phase1-product-requirements/README.md",
        (r"Stage-02a|requirements-structural-analysis", r"Stage-02b|requirements-specification-deepening"),
    ),
    (
        "skills-structure doc acknowledges Stage-02a / Stage-02b split",
        "docs/phases/phase-1/phase-1-skills-structure-v0.1.md",
        (r"Stage-02a|requirements-structural-analysis", r"Stage-02b|requirements-specification-deepening"),
    ),
    (
        "authoring-basis doc acknowledges Stage-02a / Stage-02b split",
        "docs/phases/phase-1/phase-1-skill-authoring-basis-v0.1.md",
        (r"Stage-02a|requirements-structural-analysis", r"Stage-02b|requirements-specification-deepening"),
    ),
    (
        "convergence-driver doc acknowledges Stage-02a / Stage-02b split",
        "docs/phases/phase-1/phase-1-convergence-driver-v0.1.md",
        (r"Stage-02a|requirements-structural-analysis", r"Stage-02b|requirements-specification-deepening"),
    ),
    (
        "thinking-runtime-layer doc acknowledges Stage-02a / Stage-02b split",
        "docs/phases/phase-1/phase-1-thinking-runtime-layer-v0.1.md",
        (r"Stage-02a|requirements-structural-analysis", r"Stage-02b|requirements-specification-deepening"),
    ),
    (
        "minimum-admission doc acknowledges Stage-02a / Stage-02b split",
        "docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md",
        (r"Stage-02a|requirements-structural-analysis", r"Stage-02b|requirements-specification-deepening"),
    ),
    (
        "robustness-coverage doc acknowledges Stage-02a / Stage-02b split",
        "docs/phases/phase-1/phase-1-robustness-coverage-v0.1.md",
        (r"Stage-02a|requirements-structural-analysis", r"Stage-02b|requirements-specification-deepening"),
    ),
    (
        "zh execution-report template acknowledges Stage-02a / Stage-02b split",
        "docs/phases/phase-1/phase-1-execution-report-template.zh-CN.md",
        (r"stage_02a_output", r"stage_02b_output"),
    ),
)

GENERATED_STAGE_FILES = {
    "stage_01": "stage-01-user-research.md",
    "stage_02a": "stage-02a-requirements-structural-analysis.md",
    "stage_02b": "stage-02b-requirements-specification-deepening.md",
    "stage_03": "stage-03-requirements-decomposition-and-mvp-slicing.md",
    "stage_04": "stage-04-requirements-validation-and-concept-proof.md",
}

CRITICAL_PRD_SECTIONS = (
    r"##\s+(?:8\.\s+)?[^\n]*Requirements Structure[^\n]*$",
    r"##\s+(?:11\.\s+)?[^\n]*Information Architecture Direction[^\n]*$",
    r"##\s+(?:12\.\s+)?[^\n]*MVP Definition & Scope[^\n]*$",
    r"##\s+(?:13\.\s+)?[^\n]*Validation Strategy & Current Conclusion[^\n]*$",
    r"##\s+(?:18\.\s+)?[^\n]*Handoff to Design / Architecture[^\n]*$",
)

GENERATOR_EXPECTED_KEYS = ("stage_01", "stage_02a", "stage_02b", "stage_03", "stage_04")
CONVERGENCE_RUNTIME_EXPECTATIONS = (
    (
        "convergence script exists",
        "scripts/phase1/phase1_converge_prd.py",
        (r"Converge an audit-rich Phase-1 PRD", r"convergence evidence"),
    ),
    (
        "runtime snapshot records convergence script",
        "scripts/phase1/record_phase1_runtime_snapshot.py",
        (r"phase1_converge_prd\.py",),
    ),
    (
        "runtime snapshot records report emitter and full trial runner",
        "scripts/phase1/record_phase1_runtime_snapshot.py",
        (r"phase1_emit_execution_report\.py", r"phase1_emit_depth_runtime_artifacts\.py", r"run_phase1_full_trial\.py"),
    ),
    (
        "convergence driver documents audit-rich and converged PRD separation",
        "docs/phases/phase-1/phase-1-convergence-driver-v0.1.md",
        (r"audit-rich", r"converged PRD|final PRD", r"phase1_converge_prd\.py"),
    ),
)

FULL_RUN_RUNTIME_EXPECTATIONS = (
    (
        "execution report emitter exists",
        "scripts/phase1/phase1_emit_execution_report.py",
        (r"Emit a Phase-1 execution report", r"Deliverable Verdict Matrix|PRD Convergence Conclusion"),
    ),
    (
        "one-click full trial runner exists",
        "scripts/phase1/run_phase1_full_trial.py",
        (
            r"One-click Phase-1 full trial runner",
            r"phase1_generate_deep_stage_outputs\.py",
            r"phase1_emit_depth_runtime_artifacts\.py",
            r"phase1_emit_execution_report\.py",
            r"emit-legacy-zh-cn-mirror",
            r"localized_reader_evidence_state|legacy_zh_cn_audit_mirror|deprecated deterministic zh-CN audit mirror",
        ),
    ),
)

OPTIONAL_READER_RUNTIME_EXPECTATIONS = (
    (
        "LLM reader translation runner exists",
        "scripts/common/emit_reader_translation.py",
        (r"localized reader artifact", r"OpenAI-compatible|OPENAI_BASE_URL|OPENAI_API_KEY", r"package_reader_artifact"),
    ),
    (
        "reader artifact integrity checker exists",
        "scripts/common/reader_artifact_integrity.py",
        (r"immutable tokens", r"render_reader_preamble|check_integrity"),
    ),
)

MINDTHUS_METHOD_RUNTIME_EXPECTATIONS = (
    (
        "Mindthus 3L5S method exists",
        "runtime-deps/mindthus/release/skills/3l5s/SKILL.md",
        (r"Three Layers \+ Five Steps", r"Discovery -> Definition -> Resolution", r"Baseline -> Target"),
    ),
    (
        "Mindthus 3L5S recursive loop exists",
        "runtime-deps/mindthus/release/skills/3l5s/resources/three-layer-recursive-loop.md",
        (r"Discovery", r"Definition", r"Resolution"),
    ),
    (
        "Mindthus router exists",
        "runtime-deps/mindthus/release/skills/using-mindthus/SKILL.md",
        (r"Mindthus default posture", r"3l5s", r"wae"),
    ),
    (
        "Mindthus WAE method exists",
        "runtime-deps/mindthus/release/skills/wae/SKILL.md",
        (r"Workflow should control order", r"Agentic reasoning", r"Evidence should connect claims"),
    ),
    (
        "evidence and uncertainty protocol exists",
        "docs/governance/evidence-and-uncertainty-protocol-v0.1.md",
        (r"review-bound", r"downstream honesty", r"statement classes"),
    ),
    (
        "maturity and confidence protocol exists",
        "docs/governance/maturity-and-confidence-protocol-v0.1.md",
        (
            r"delivery readiness",
            r"evidence confidence",
            r"safe_start_scope|safe downstream action",
            r"warning / pending external confirmation|business completeness",
        ),
    ),
    (
        "deepening and freeze protocol exists",
        "docs/governance/deepening-and-freeze-protocol-v0.1.md",
        (r"Valid Reasons to Deepen", r"freeze-with-review-bound-warning", r"Minimum Per-Round Trace"),
    ),
    (
        "handoff and convergence protocol exists",
        "docs/governance/handoff-and-convergence-protocol-v0.1.md",
        (
            r"Required Handoff Packet",
            r"Convergence Rule",
            r"Safe-Start Rule",
            r"warning_or_pending_confirmation_ledger|document-complete but still business-incomplete",
        ),
    ),
)

STAGE_02B_AUDIT_EXPECTATIONS = (
    "self-test-case.md",
    "self-test-dry-run-output.md",
    "self-test-verification-report.md",
    "robustness-test-case.md",
    "robustness-test-report.md",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def source_cards_path(repo_root: Path, stage_key: str) -> Path:
    return (repo_root / STAGE_PACKS[stage_key]["dir"] / "source-cards.md").resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase-1 skill/runtime family completeness")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--prd")
    parser.add_argument("--prd-zh")
    parser.add_argument("--convergence-evidence")
    parser.add_argument("--stage-dir")
    parser.add_argument("--generator", default="scripts/phase1/phase1_generate_deep_stage_outputs.py")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    generator_path = (repo_root / args.generator).resolve()
    prd_path = Path(args.prd).resolve() if args.prd else None
    prd_zh_path = Path(args.prd_zh).resolve() if args.prd_zh else None
    convergence_evidence_path = Path(args.convergence_evidence).resolve() if args.convergence_evidence else None
    stage_dir = Path(args.stage_dir).resolve() if args.stage_dir else None

    print("== Phase-1 Skill Family Audit ==")
    print(f"repo_root: {repo_root}")
    if prd_path:
        print(f"prd: {prd_path}")
    if prd_zh_path:
        print(f"prd_zh: {prd_zh_path}")
    if stage_dir:
        print(f"stage_dir: {stage_dir}")
    print(f"generator: {generator_path}")

    blocked = False
    warnings = 0

    print("\n-- Runtime Pack Completeness --")
    for key, config in STAGE_PACKS.items():
        pack_dir = (repo_root / config["dir"]).resolve()
        if not pack_dir.exists():
            print(f"[BLOCKED] missing stage pack directory: {pack_dir}")
            blocked = True
            continue
        missing = [name for name in config["required_runtime_files"] if not (pack_dir / name).exists()]
        if missing:
            print(f"[BLOCKED] {key} missing runtime files: {', '.join(missing)}")
            blocked = True
        else:
            print(f"[PASS] {key} runtime pack complete")

    print("\n-- Generator Asset Coverage --")
    if not generator_path.exists():
        print(f"[BLOCKED] generator not found: {generator_path}")
        blocked = True
    else:
        generator_text = read_text(generator_path)
        for key in GENERATOR_EXPECTED_KEYS:
            if re.search(rf'"{re.escape(key)}"\s*:', generator_text):
                print(f"[PASS] STAGE_ASSET_PATHS covers {key}")
            else:
                print(f"[BLOCKED] STAGE_ASSET_PATHS missing {key}")
                blocked = True
        for key in GENERATOR_EXPECTED_KEYS:
            if re.search(
                rf'load_stage_skill_assets\(\s*"{re.escape(key)}"\s*\)',
                generator_text,
                flags=re.MULTILINE,
            ):
                print(f"[PASS] runtime materially loads assets for {key}")
            else:
                print(f"[BLOCKED] runtime does not visibly load assets for {key}")
                blocked = True

    print("\n-- Generated Stage Evidence --")
    if stage_dir is None:
        print("[WARNING] stage output directory not provided; generated-stage audit skipped")
        warnings += 1
    else:
        for key, filename in GENERATED_STAGE_FILES.items():
            path = stage_dir / filename
            if not path.exists():
                print(f"[BLOCKED] missing generated stage output: {path}")
                blocked = True
                continue
            text = read_text(path)
            required_patterns = (
                r"Skill Asset Ingestion Snapshot",
                r"source_bundles_loaded",
                r"current_use_rules_compiled",
                r"Minimal Reasoning Unit Ledger",
                r"decision_effect",
                r"downstream_handoff",
            )
            missing_patterns = [
                pattern for pattern in required_patterns if not re.search(pattern, text, flags=re.IGNORECASE)
            ]
            if missing_patterns:
                print(f"[BLOCKED] {key} missing generated asset-trace signals: {', '.join(missing_patterns)}")
                blocked = True
            else:
                print(f"[PASS] {key} generated output retains asset-ingestion evidence")

    print("\n-- Documentation Alignment --")
    for label, rel_path, patterns in DOC_EXPECTATIONS:
        path = (repo_root / rel_path).resolve()
        if not path.exists():
            print(f"[WARNING] missing documentation file: {path}")
            warnings += 1
            continue
        text = read_text(path)
        missing = [pattern for pattern in patterns if not re.search(pattern, text, flags=re.IGNORECASE)]
        if missing:
            print(f"[WARNING] {label} not fully reflected in {path.name}")
            warnings += 1
        else:
            print(f"[PASS] {label}")

    print("\n-- Convergence Runtime Layer --")
    for label, rel_path, patterns in CONVERGENCE_RUNTIME_EXPECTATIONS:
        path = (repo_root / rel_path).resolve()
        if not path.exists():
            print(f"[BLOCKED] missing convergence runtime artifact: {path}")
            blocked = True
            continue
        text = read_text(path)
        missing = [pattern for pattern in patterns if not re.search(pattern, text, flags=re.IGNORECASE)]
        if missing:
            print(f"[BLOCKED] {label} not fully reflected in {path.name}")
            blocked = True
        else:
            print(f"[PASS] {label}")

    print("\n-- Full-Run Runtime Layer --")
    for label, rel_path, patterns in FULL_RUN_RUNTIME_EXPECTATIONS:
        path = (repo_root / rel_path).resolve()
        if not path.exists():
            print(f"[BLOCKED] missing full-run runtime artifact: {path}")
            blocked = True
            continue
        text = read_text(path)
        missing = [pattern for pattern in patterns if not re.search(pattern, text, flags=re.IGNORECASE)]
        if missing:
            print(f"[BLOCKED] {label} not fully reflected in {path.name}")
            blocked = True
        else:
            print(f"[PASS] {label}")

    print("\n-- Optional Localized Reader Evidence Layer --")
    for label, rel_path, patterns in OPTIONAL_READER_RUNTIME_EXPECTATIONS:
        path = (repo_root / rel_path).resolve()
        if not path.exists():
            print(f"[BLOCKED] missing optional reader runtime artifact: {path}")
            blocked = True
            continue
        text = read_text(path)
        missing = [pattern for pattern in patterns if not re.search(pattern, text, flags=re.IGNORECASE)]
        if missing:
            print(f"[BLOCKED] {label} not fully reflected in {path.name}")
            blocked = True
        else:
            print(f"[PASS] {label}")
    print("[PASS] legacy deterministic zh-CN mirror is compatibility-only, not required P1 mainline evidence")

    print("\n-- Mindthus Method Layer --")
    for label, rel_path, patterns in MINDTHUS_METHOD_RUNTIME_EXPECTATIONS:
        path = (repo_root / rel_path).resolve()
        if not path.exists():
            print(f"[BLOCKED] missing Mindthus method artifact: {path}")
            blocked = True
            continue
        text = read_text(path)
        missing = [pattern for pattern in patterns if not re.search(pattern, text, flags=re.IGNORECASE)]
        if missing:
            print(f"[BLOCKED] {label} not fully reflected in {path.name}")
            blocked = True
        else:
            print(f"[PASS] {label}")

    print("\n-- Source-Card Method Wiring --")
    kernel_patterns = (
        r"runtime-deps/mindthus/release/skills/3l5s/SKILL\.md",
        r"runtime-deps/mindthus/release/skills/3l5s/resources/three-layer-recursive-loop\.md",
        r"runtime-deps/mindthus/release/skills/using-mindthus/SKILL\.md",
        r"evidence-and-uncertainty-protocol-v0\.1\.md",
        r"maturity-and-confidence-protocol-v0\.1\.md",
        r"deepening-and-freeze-protocol-v0\.1\.md",
        r"handoff-and-convergence-protocol-v0\.1\.md",
    )
    for stage_key in STAGE_PACKS:
        path = source_cards_path(repo_root, stage_key)
        if not path.exists():
            print(f"[BLOCKED] source cards not found for {stage_key}: {path}")
            blocked = True
            continue
        text = read_text(path)
        missing = [pattern for pattern in kernel_patterns if not re.search(pattern, text, flags=re.IGNORECASE)]
        if missing:
            print(f"[BLOCKED] {stage_key} source cards missing Mindthus method-kernel wiring")
            blocked = True
        else:
            print(f"[PASS] {stage_key} source cards reference the Mindthus method kernel")

    print("\n-- Stage-02b Audit Coverage --")
    stage_02b_dir = (repo_root / STAGE_PACKS["stage_02b"]["dir"]).resolve()
    for name in STAGE_02B_AUDIT_EXPECTATIONS:
        path = stage_02b_dir / name
        if path.exists():
            print(f"[PASS] Stage-02b audit asset exists: {name}")
        else:
            print(f"[BLOCKED] Stage-02b audit asset missing: {name}")
            blocked = True

    print("\n-- PRD Example Coverage --")
    if prd_path is None:
        print("[WARNING] PRD path not provided; PRD example audit skipped")
        warnings += 1
    else:
        if not prd_path.exists():
            print(f"[BLOCKED] PRD not found: {prd_path}")
            blocked = True
        else:
            prd_text = read_text(prd_path)
            for pattern in CRITICAL_PRD_SECTIONS:
                if re.search(pattern, prd_text, flags=re.IGNORECASE | re.MULTILINE):
                    print(f"[PASS] PRD section present: {pattern}")
                else:
                    print(f"[BLOCKED] PRD section missing: {pattern}")
                    blocked = True
            if re.search(r"Analysis Delta Ledger", prd_text, flags=re.IGNORECASE):
                print("[PASS] PRD keeps inline Analysis Delta Ledger")
            elif convergence_evidence_path and convergence_evidence_path.exists():
                evidence_text = read_text(convergence_evidence_path)
                if re.search(r"Analysis Delta Ledger", evidence_text, flags=re.IGNORECASE):
                    print("[PASS] Analysis Delta Ledger preserved in external convergence evidence")
                else:
                    print("[BLOCKED] external convergence evidence missing Analysis Delta Ledger")
                    blocked = True
            else:
                print("[BLOCKED] no inline or external Analysis Delta Ledger found")
                blocked = True

    print("\n-- zh-CN PRD Mirror Coverage --")
    if prd_zh_path is None:
        print("[WARNING] zh-CN PRD path not provided; zh audit mirror check skipped")
        warnings += 1
    elif not prd_zh_path.exists():
        print(f"[BLOCKED] zh-CN PRD not found: {prd_zh_path}")
        blocked = True
    else:
        prd_zh_text = read_text(prd_zh_path)
        mirror_patterns = (
            r"中文评审镜像|zh-CN audit mirror",
            r"canonical_of:",
            r"问题陈述\s*\(Problem Statement\)|领域模型\s*\(Domain Model\)|信息架构方向\s*\(Information Architecture Direction\)|目标用户与关键角色\s*\(Target Users & Key Roles\)",
            r"文档交付状态|证据置信状态",
        )
        missing = [pattern for pattern in mirror_patterns if not re.search(pattern, prd_zh_text, flags=re.IGNORECASE)]
        if missing:
            print("[BLOCKED] zh-CN PRD mirror is missing bilingual review signals")
            blocked = True
        else:
            print("[PASS] zh-CN PRD mirror retains review-note and bilingual critical terminology")

    print("\n-- Verdict --")
    print(f"warnings: {warnings}")
    if blocked:
        print("FINAL: BLOCKED")
        return 2
    print("FINAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
