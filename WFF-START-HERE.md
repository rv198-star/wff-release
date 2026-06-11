# WFF Start Here

This is the low-context first-read file for this install pack.
Use it to choose an entry before opening the full README, skill catalog, scripts, or docs tree.

## Pick The Entry
| Task | Start with | Then read |
|---|---|---|
| Decide whether WFF should be used and choose an entry | `skills/using-wff/SKILL.md` | a WFF admission decision, one of three external entry routes, or a normal non-WFF path |
| Start New Work: rough idea, conversation, or scattered materials | `skills/wff-req-chat/SKILL.md` | P1 source input packet, then `skills/wff-req/SKILL.md` when included |
| Stable requirements -> PRD | `skills/wff-req/SKILL.md` | generated P1 PRD and score reports |
| internal continuation: WFF P1 -> engineering design, not an external entry | `skills/wff-arch/SKILL.md` | P2 `engineering-spec-pack.md` and `phase-3-implementation-entry.md` after WFF-native P1 truth is accepted |
| internal continuation: WFF P2 -> implementation and tests, not an external entry | `skills/wff-impl/SKILL.md` | P3 action cards, implementation review, and verification reports after a WFF-native P2 handoff |
| internal continuation: WFF P3 -> closure judgment, not an external entry | `skills/wff-validation/SKILL.md` | P4 validation report and closure summary after WFF-native P3 evidence exists |
| external entry: code-backed existing-system assessment for legacy/refactor/migration/capacity work | `skills/wff-x/SKILL.md` | PX baseline, truth state, gaps, risks, target package, safety net, and route recommendation; Related documents are supporting evidence, standalone documents are not enough |
| Role-based use | `docs/WFF-ROLE-AGENTS.zh-CN.md` | role adapter output plus the underlying lifecycle skill |

## Read Only Three Document Classes First
| Class | What to open | Why |
|---|---|---|
| Human core | `README.md`, this file, `docs/WFF-ROLE-AGENTS.zh-CN.md` when using roles | User entry and task routing |
| Generated handoff | P1 PRD, P2 engineering spec, P3 action cards/review, P4 closure summary, PX baseline/target package | The small set humans usually need to judge progress |
| Evidence and diagnostics | score reports, ledgers, runtime smoke, targeted reports, install-pack audit | Proof, debugging, and claim ceilings; read on demand |

Do not start by recursively reading every file in `scripts/`, `docs/`, or `reference-packages/`.

## Pack Files
- `README.md`: install layout, root commands, support-directory rules, and links to detailed runtime notes.
- `AGENTS.md`: concise agent-facing operating guidance for this install pack.
- `SKILL_INSTALL_PACK_MANIFEST.json`: exact included skills, scripts, docs, references, and profile metadata.
- pack_name: `wff-v1.5.3-skills-install-pack`
- install_set_id: `full-pack`
