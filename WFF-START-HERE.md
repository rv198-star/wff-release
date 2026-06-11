# WFF Start Here

This is the low-context first-read file for this install pack.
Use it before scanning the full README, skill catalog, scripts, or docs tree.

## Pick The Entry
| Task | Start with | Then read |
|---|---|---|
| Rough idea or scattered notes | `skills/wff-req-chat/SKILL.md` | `skills/wff-req/SKILL.md` when included |
| Stable requirements -> PRD | `skills/wff-req/SKILL.md` | generated P1 PRD and score reports |
| PRD -> engineering design | `skills/wff-arch/SKILL.md` | P2 `engineering-spec-pack.md` and `phase-3-implementation-entry.md` |
| Design -> implementation and tests | `skills/wff-impl/SKILL.md` | P3 action cards, implementation review, verification reports |
| Implementation -> closure judgment | `skills/wff-validation/SKILL.md` | P4 validation report and closure summary |
| Existing system change, refactor, migration, or capacity work | `skills/wff-x/SKILL.md` | PX baseline, risks, target package, and safety net |
| Role-based use | `docs/WFF-ROLE-AGENTS.zh-CN.md` | role adapter output plus the underlying lifecycle skill |

## Read Only Three Document Classes First
| Class | What to open | Why |
|---|---|---|
| Human core | `README.md`, this file, `docs/WFF-ROLE-AGENTS.zh-CN.md` when using roles | User entry and task routing |
| Generated handoff | P1 PRD, P2 engineering spec, P3 action cards/review, P4 closure summary, PX baseline/target package | The small set humans usually need to judge progress |
| Evidence and diagnostics | score reports, ledgers, runtime smoke, full-targeted reports, install-pack audit | Proof, debugging, and claim ceilings; read on demand |

Do not start by recursively reading every file in `scripts/`, `docs/`, or `reference-packages/`.

## Runtime Expectation
- P3 strict runtime validation is expected to dominate runtime cost; retained v1.4/v1.4.1 proof evidence showed about `96%` of recorded phase-step time in P3.
- The main driver is full-targeted SQL / contract / scenario / replay evidence, not Docker build alone.
- Fast or focused paths (`--validation-level fast` / `--validation-level focused`) run critical targeted evidence and do not auto-run runtime smoke unless explicitly requested; they do not replace release-proof strict evidence.

## Pack Files
- `README.md`: installation layouts, root commands, runtime notes, and metadata.
- `AGENTS.md`: concise agent-facing operating guidance for this install pack.
- `SKILL_INSTALL_PACK_MANIFEST.json`: exact included skills, scripts, docs, references, and profile metadata.
- pack_name: `wff-v1.4.2-skills-install-pack`
- install_set_id: `full-pack`
