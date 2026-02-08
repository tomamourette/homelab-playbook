# Technical Research

**Phase:** 1 — Analysis | **Agent:** Analyst (Mary) | **Model:** Gemini Pro or `/model reason` | **Cost:** $0-0.05

## When to Use

Investigate technical feasibility, evaluate technologies, or research implementation approaches. Also used during Phase 4 before a correct-course action.

## Execution

Handle locally. Start on Gemini Pro. For complex architecture trade-offs, suggest switching to `/model reason` (DeepSeek R1).

1. Identify the technical question from the user or product brief
2. Research and document:
   - Technology options with pros/cons
   - Compatibility with existing homelab stack (Docker, Terraform, Ansible, Traefik)
   - Performance and resource implications
   - Security considerations
   - Migration complexity (if replacing something)
3. If evaluating complex trade-offs, suggest: "This is a complex evaluation — switch to `/model reason` for deeper analysis"
4. Write findings to `docs/research/technical-research.md`

## Model Escalation

- **Gemini Pro:** Standard technology evaluation, documentation lookup
- **`/model reason`:** Complex architecture trade-offs, multi-system integration analysis, performance modeling
