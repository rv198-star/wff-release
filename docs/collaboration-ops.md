# Collaboration Ops: Meta-Skills Owner + Extraction Operator

## Purpose

This document removes the human-as-messenger bottleneck.

Use it as the shared interface between:
- Role A: Meta-Skills Owner (governance/rules/skill evolution)
- Role B: Extraction Operator (round execution and convergence work)

The user should only review round status and decisions, not relay operational details between sessions.

---

## Roles and Responsibilities

### Role A — Meta-Skills Owner + Auditor
Primary owner: Meta Skill rules, governance logic, audit standards, and project-memory updates.

Responsibilities:
- maintain `skills/wff-meta-book-to-skills-extraction/`
- maintain `skills/wff-meta-corpus-extraction-governance/`
- update governance controls when repeated failures appear
- run independent audits on delivered round artifacts
- decide PASS/WARN/DEFER rule changes (not case-by-case exceptions)
- publish version updates and changelog notes
- ingest confirmed round bundles back into repo
- update project memory and release notes after accepted rounds

### Role B — Extraction Operator / 落地执行者
Primary owner: external-workspace execution, evidence production, merge/promotion/staging convergence delivery.

Responsibilities:
- run extraction/merge/promotion rounds in external workspace
- produce all required round control artifacts
- keep decisions evidence-bound (cross-source, gate, diagram)
- avoid prohibited anti-patterns (aesthetic promotion, over-merge, card-volume theater)
- submit round bundle and self-audit summary

Not responsible for:
- modifying project-level Meta Skills rule bodies
- relaxing gate / promotion standards
- self-upgrading WARN to PASS without evidence change
- defining new canonical rules outside Owner verdicts

---

## Shared Contract (Interface)

Every round must pass through the same interface:

### B -> A (Operator handoff)
Required bundle:
1. merge decisions
2. merge ledger
3. promotion decisions
4. diagram gate evidence
5. main-repo absorption map
6. next queue
7. gate review

Required summary fields:
- scope (clusters processed)
- strict constraints obeyed
- final staged verdict
- blockers list

### A -> B (Owner feedback)
Feedback must be structured as:
- `VERDICT`: PASS / WARN / FAIL
- `BLOCKERS`: concrete, countable, evidence-linked
- `ALLOWED NEXT ACTIONS`: max 1-3 actions
- `FORBIDDEN ACTIONS`: explicit anti-drift constraints

No vague advice. No style-only review.

---

## Round Cadence

### Execution Loop
1. Operator executes one bounded round
2. Operator emits round bundle + self-check
3. Owner performs independent audit
4. Owner publishes verdict + blockers
5. Operator executes only blocker-focused next round

### Scope Control Rules
- Default max: 1-2 merge clusters per round
- No large card-volume expansion during convergence rounds
- No canonical promotion without evidence-complete checks

---

## Audit-Driven Rule Evolution

When the same failure appears in 2+ rounds:
- Owner must update Meta Skill rules (not just ad-hoc comments)
- Owner must add/adjust pressure scenario tests
- Owner must document change in changelog

This keeps governance logic alive and evidence-based.

---

## Round Status Template (Single Source of Truth)

Use this block in every handoff message between A and B:

```text
ROUND: <round-id>
SCOPE: <clusters or bounded target>
DELIVERED_ARTIFACTS: <file list>
STRICT_CONSTRAINTS: <obeyed/not-obeyed>
PROMOTION_OUTCOME: <PASS/WARN/DEFER summary>
STAGED_VERDICT: <one-line verdict>
BLOCKERS: <numbered blocker list>
NEXT_ALLOWED_ACTIONS: <1-3 actions>
CHECK: <machine-checkable result>
```

If this block is missing, handoff is invalid and should not be audited as a complete round result.

---

## Storage Convention

### In-repo (authoritative history)
- `skills/` for Meta Skills and changelogs
- `archive/extraction-runs/round-XX/` for ingested round bundles
- `findings.md`, `task_plan.md`, `progress.md` for project memory

### External workspace (execution workspace)
- extraction operator may continue active work externally
- only round-complete bundles are ingested back into repo

---

## Escalation Rules

Escalate to user only when one of these is true:
1. contradictory strategic constraints
2. blocker requires business/policy decision outside current rules
3. repeated failure persists after rule update + one retry round

Everything else should stay inside A<->B loop.

---

## Current Operating Mode

- System default: docs-first, AI-first, artifact/gate controlled
- Current phase: convergence and blocker-focused remediation
- Method adoption strategy: SOMA/process-orchestration/service-orchestration as high-order method assets first, deeper integration later
