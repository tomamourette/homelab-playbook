---
stepsCompleted: [init, research, synthesis]
inputDocuments: [karpathy/autoresearch, community-usage, bmad-skill-analysis]
workflowType: 'research'
lastStep: 3
research_type: 'technical'
research_topic: 'autoresearch-bmad-integration'
research_goals: 'Map autoresearch patterns to BMAD workflow for code quality and skill self-improvement'
user_name: 'tomamourette'
date: '2026-04-04'
web_research_enabled: true
source_verification: true
---

# Research Report: Autoresearch Integration with BMAD Workflow

**Date:** 2026-04-04
**Author:** tomamourette
**Research Type:** Technical — Exploratory (potential future epic)

---

## Executive Summary

This report investigates how Karpathy's autoresearch pattern — autonomous modify-verify-keep/discard iteration — can be integrated into the BMAD development workflow. Two approaches are analyzed:

1. **Code Quality Loop** — Using eval assertions from stories to drive autoresearch iteration on implementation code, either during dev-story or after code-review.
2. **Skill Evolution Loop** — Using session output (review findings, deferred work, dev confusion signals) to improve the BMAD skills themselves (create-story, dev-story, code-review).

**Key finding:** Approach 1 is near-ready. The existing `create-story-with-evals` + `/autoresearch:fix` pipeline already implements the core pattern. Two small tooling gaps (eval-runner script, review-to-fix-queue parser) would close the loop. Approach 2 is a research project requiring substantial eval infrastructure for measuring prompt/skill quality.

**Perplexity clarification:** Perplexity AI has no relationship to Karpathy's autoresearch. The confusion stems from Perplexity Computer (a general-purpose AI agent platform) being announced around the same time. Autoresearch is agent-agnostic and works with any coding agent including Claude Code.

---

## 1. What is Karpathy's Autoresearch?

### Purpose and Philosophy

Autoresearch (released March 2026, 65K+ GitHub stars) is a minimal framework that hands the ML experimentation loop to an AI coding agent. The entire repo is deliberately tiny — three files, ~630 lines of Python. The insight: most research/engineering is methodical iteration that doesn't require human creativity for every step.

**The paradigm shift:** The human edits `program.md` (strategy, constraints, what to try). The AI edits `train.py` (the actual code). As Karpathy puts it, the human writes the "research org code" — the instructions — not the implementation.

**Results:** Left running for ~2 days, it found ~20 improvements to a training pipeline Karpathy had already hand-tuned for months, yielding an 11% speedup. Shopify CEO Tobi Lutke ran 37 experiments overnight and got a 0.8B model outperforming his hand-tuned 1.6B model.

### Core Algorithm

```
LOOP FOREVER:
  1. Examine git state (current branch/commit)
  2. Form hypothesis, modify code with ONE experimental idea
  3. git commit the change (enables clean rollback)
  4. Run experiment with FIXED TIME BUDGET (5 min)
  5. Read results: single numerical metric
  6. If crash → attempt fix or move on
  7. Log results to TSV
  8. If metric IMPROVED → KEEP (advance branch)
  9. If metric SAME or WORSE → DISCARD (git reset)
```

### Key Properties

| Property | Value | Why it Matters |
|----------|-------|----------------|
| **Single metric** | `val_bpb` (bits per byte) | No ambiguity about "better" |
| **Fixed time budget** | 300s per experiment | Experiments are directly comparable |
| **Atomic changes** | One idea per commit | Clean rollback, no confounding variables |
| **Never stop** | Agent runs until interrupted | ~12 experiments/hour, ~100 overnight |
| **Three files** | `program.md` (human), `train.py` (agent), `prepare.py` (locked) | Clear ownership boundaries |

### What Autoresearch is NOT

- **Not novel research** — It iterates on a well-defined search space, not inventing new paradigms
- **Not for subjective tasks** — Requires a clear, fast, objective metric
- **Not related to Perplexity** — Zero dependency on or integration with Perplexity AI
- **Not for large codebases** — Works best on isolated, small files (<5K lines)
- **Not fully autonomous** — Best as "overnight automation with morning review"

---

## 2. Community Usage Patterns

### Highest-ROI Use Cases (Community Consensus)

1. **Claude Code skills and system prompts** — Text-only, isolated, measurable. The ideal autoresearch target.
2. **Performance optimization** — Code with strong test coverage and clear benchmarks (Shopify: 53% faster rendering, 61% fewer allocations over 120 experiments).
3. **ML experimentation** — The original and most validated use case.

### Best Practices (Non-Negotiable Prerequisites)

1. **Binary eval criteria only.** No 1-7 scales — they cause gaming. Every assertion must be yes/no.
2. **3-6 criteria optimal.** Below 3, agents exploit loopholes. Above 6, agents game the checklist.
3. **Single file to modify per iteration.** Multi-file changes create confounding variables.
4. **Existing test suite as guard rail.** The loop optimizes the metric; tests ensure correctness.
5. **Persistent memory (program.md).** Without it, agents explore randomly and repeat failed directions.

### Anti-Patterns to Avoid

| Anti-Pattern | Why it Fails |
|-------------|-------------|
| Vague/subjective evaluation | Loop wanders without convergence |
| Multi-file changes per iteration | Can't determine which change caused failure |
| Human-in-the-loop eval | Breaks autonomous execution |
| No persistent memory | Random exploration, repeated failures |
| Extended evaluation windows (30+ min) | Kills exploration velocity |
| Multiple competing metrics | Ambiguous tradeoffs break keep/discard decision |
| Skipping guard rails (test suite) | Metric improves but correctness regresses |

### Cost Profile

- ~$0.10/cycle (~18K tokens)
- 50-round overnight: ~$5
- 100-round deep: $10-25
- ~12 experiments/hour

---

## 3. Our Current Autoresearch Capabilities

The installed `/autoresearch` skill has 10 modes:

| Mode | Purpose | BMAD Relevance |
|------|---------|----------------|
| `/autoresearch` | Core modify-verify-keep/discard loop | General |
| `/autoresearch:fix` | Fix errors one at a time until zero remain | **Primary integration — code review findings** |
| `/autoresearch:debug` | Scientific method bug hunting | Post-dev debugging |
| `/autoresearch:learn` | Codebase documentation engine | End-of-epic doc refresh |
| `/autoresearch:security` | STRIDE + OWASP security audit | Security stories |
| `/autoresearch:reason` | Adversarial refinement (generate-critique-synthesize-judge) | **Skill evolution proposals** |
| `/autoresearch:scenario` | Edge case exploration across 12 dimensions | Pre-dev story analysis |
| `/autoresearch:predict` | Multi-persona swarm analysis | Pre-dev risk assessment |
| `/autoresearch:plan` | Goal → verified config wizard | Setup |
| `/autoresearch:ship` | Universal shipping checklist | Deployment stories |

**Current BMAD integration:** Only one formal touchpoint — `create-story-with-evals` generates eval assertions designed to feed `/autoresearch:fix`.

---

## 4. Approach 1: Code Quality Loop

### How It Works

The BMAD workflow already has the building blocks for an autoresearch-powered code quality loop:

```
create-story-with-evals → eval assertions (binary pass/fail)
     ↓
dev-story → implements code (assertions start failing → passing)
     ↓
code-review → produces findings (D/P/W categorized)
     ↓
autoresearch:fix → iterates through findings until zero remain
     ↓
verify → all eval assertions pass, all review findings resolved
```

### Eval Assertions Map to Autoresearch's "Verify" Step

| Autoresearch Concept | BMAD Equivalent |
|---------------------|----------------|
| Metric | Number of passing eval assertions (higher = better) |
| Verify command | Run all assertion commands, count passes |
| Direction | Higher is better (more passing = better) |
| Guard | Existing tests / typecheck that must not regress |
| Baseline | Zero passing (pre-implementation) |
| Target | 100% passing (all assertions green) |

### Where to Trigger Autoresearch

**Trigger Point A: During dev-story (replacing manual TDD)**

The TDD red-green cycle IS the autoresearch loop:
- Red = eval assertion fails (error detected)
- Green = fix one assertion (atomic change + verify)
- Refactor = guard passes, code quality maintained

This works best for **infrastructure stories** (epics 1-3) where assertions are shell-executable: binary exists, service running, config correct.

**Trigger Point B: After code-review (the designed integration point)**

Code review findings become the error list. `/autoresearch:fix` iterates:
- D-findings (design) → Priority 2
- P-findings (patches) → Priority 5-6
- W-findings (deferred) → not included (logged separately)

This is the integration the eval assertions were built for. In our session today, we manually applied patches D1-D3 and P1-P6 during code review. Autoresearch:fix would have done this autonomously.

**Recommendation: Trigger Point B (after code-review) is the natural first integration.** It has the clearest input (structured findings), the most mechanical fixes (patch-category findings), and the highest confidence in eval criteria.

### What's Missing (Gaps)

| Gap | Description | Effort | Priority |
|-----|------------|--------|----------|
| **G1: eval-runner script** | Run all eval assertions from a story file, output `N/M passed` | Small | Immediate |
| **G2: review-to-fix-queue parser** | Parse `[Review][Patch]` findings from story files into autoresearch:fix format | Small | Immediate |
| **G3: story path resolver** | Auto-detect current story from sprint-status.yaml | Small | Next sprint |
| **G4: guard command per story type** | Homelab has no `npm test` — guards need to be story-type-aware | Medium | Next sprint |
| **G5: post-fix story update** | Auto-mark review findings `[x]` after autoresearch:fix resolves them | Small | Next sprint |

### Concrete Example: How Today's Session Would Have Used It

After the story 0-4 code review produced 3 decisions + 6 patches:

```
# Instead of manually applying patches, run:
/autoresearch:fix

Scope: .claude/skills/bmad-update-project-docs/
Target: 9 findings from story 0-4 review (D1-D3, P1-P6)
Guard: grep -r "homelab" instructions.md workflow.md (AC-3 eval)
Metric: passing findings count (higher = better)
Direction: up

# Loop would:
# Iteration 1: Fix D1 (check mode git ref) → verify → KEEP
# Iteration 2: Fix D2 (partial select stale_docs) → verify → KEEP
# ...
# Iteration 9: Fix P6 (renumber steps) → verify → KEEP
# Result: 9/9 findings resolved, all eval assertions pass
```

---

## 5. Approach 2: Skill Evolution Loop

### The Vision

Use accumulated session data to improve the BMAD skills themselves:

```
Multiple story cycles produce data:
  - Code review finding patterns (recurring issues)
  - Deferred work accumulation (systemic gaps)
  - Dev agent confusion signals (story underspecification)
     ↓
/autoresearch:reason produces improvement proposals
     ↓
Human reviews and approves (mandatory gate)
     ↓
Skill files are modified
     ↓
Next story cycle measures: did findings decrease?
     ↓
Keep or revert the skill change
```

### Observable Signals from Sessions

| BMAD Skill | Observable Data | Improvement Signal |
|-----------|----------------|-------------------|
| create-story | Story quality, dev agent confusion | More dev clarifications = story underspecified |
| dev-story | Implementation iterations, finding count | More review findings = worse story spec |
| code-review | D/P/W categories, recurring patterns | Same finding type across stories = systemic gap |
| update-project-docs | Staleness accuracy, false positives | False positives in detection = check mode needs tuning |

### Evidence from Our Session

From `deferred-work.md`, recurring patterns are already visible:
- **W1 (date fallback baseline)** — appears in BOTH 0-4 and 0-5 reviews. Systemic design issue.
- **W3 (mode detection keyword ambiguity)** — appears in BOTH 0-4 and 0-5 reviews. Skill text needs priority rules.

These are exactly the signals a skill evolution loop would detect and propose fixes for.

### How to Measure "Better"

| Proxy Metric | Measurement | Direction |
|-------------|-------------|-----------|
| Code review finding count | D + P findings per story | Lower = better |
| Deferred work growth | New W-items per epic | Lower = better |
| Dev agent re-asks | Clarification requests in dev-story | Lower = better |
| First-attempt eval pass rate | Assertion passes before any fixes | Higher = better |

**Challenge:** These metrics are slow (one data point per story) and noisy. The autoresearch loop's strength is fast iteration, but skill quality measurement is inherently slow.

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|---------|------------|
| **Drift** — skills evolve away from proven patterns | High | Git version all skill files; diff review on every change |
| **Regression** — "improvement" makes things worse | High | Measure before/after on same-complexity story |
| **Metric gaming** — optimizing for fewer findings by weakening review | Critical | Code-review skill must remain independent of the metric |
| **Overfitting** — skills tuned for one epic fail on different types | Medium | Test changes across story types before accepting |

### What's Missing (Gaps)

| Gap | Description | Effort | Priority |
|-----|------------|--------|----------|
| **G6: cross-story metrics collector** | Aggregate findings/metrics across completed stories | Medium | Future epic |
| **G7: skill snapshot + rollback** | Version skill files before modification, rollback on regression | Small | Future epic |
| **G8: human approval gate** | Formal "pause and present" for skill changes | Medium | Future epic |
| **G9: baseline metric storage** | Persistent quality metrics per story/epic | Small | Future epic |
| **G10: prompt eval infrastructure** | Run skills on test inputs, evaluate output quality | Large | Future epic (research project) |

---

## 6. Karpathy's Autoresearch vs. Our `/autoresearch` Skill

| Dimension | Karpathy's autoresearch | Our `/autoresearch` skill |
|-----------|------------------------|--------------------------|
| **Target** | Single Python file (train.py) | Any file(s) in scope |
| **Metric** | val_bpb (validation loss) | Any shell command → number |
| **Loop** | Infinite until interrupted | Configurable max iterations |
| **Persistence** | program.md + results.tsv | TSV log + git history |
| **Domain** | ML training optimization | General-purpose (10 modes) |
| **Git integration** | Branch-based, atomic commits | Same pattern |
| **Guard rails** | OOM/crash recovery only | Configurable guard command |

**Key insight:** Our `/autoresearch` skill is already a generalized implementation of the Karpathy pattern. We don't need to port Karpathy's code — we need to wire our existing skill into our existing BMAD workflow.

---

## 7. Where Perplexity Fits (It Doesn't)

Perplexity AI has **zero relationship** to Karpathy's autoresearch:

- The autoresearch repository has no Perplexity dependency or integration
- Perplexity Computer (announced separately) is a general-purpose agent platform bundling Claude Code + GitHub CLI
- The confusion stems from both representing "autonomous AI agents on codebases" — but they are independent projects
- For our purposes, Perplexity offers no unique capability that Claude Code + autoresearch doesn't already provide

---

## 8. Recommendations

### Immediate (This Sprint — Low Effort, High Value)

**Build G1 + G2:** An `eval-runner.sh` script and a review-to-fix-queue parser. This enables running `/autoresearch:fix` directly after code-review with structured findings as input. ~1 story worth of work.

**Formalize the trigger point:** After code-review produces findings, the reviewer should suggest: "Run `/autoresearch:fix` to auto-resolve N patch findings." This is already the intended flow — just needs documentation.

### Next Epic (Medium Effort)

**Build G3-G5:** Story path resolver, per-story-type guard detection, post-fix story update. This closes the full loop: code-review → autoresearch:fix → story file updated → sprint status synced.

**Consider adding `/autoresearch:fix --from-review` mode:** Extends the fix workflow to parse code review findings from BMAD story files. Currently fix reads from `debug/*/findings.md` — a `--from-review` flag would read from the story file's `### Review Findings` section.

### Future Epic: Self-Improving BMAD (Large Effort, Research)

**Build G6-G10:** Cross-story metrics, skill versioning, human approval gates, baseline storage, prompt eval infrastructure.

**Sequencing within the epic:**
1. G6 (metrics collector) + G9 (baseline storage) — establish measurement
2. G7 (skill snapshot) — enable safe experimentation
3. G8 (human gate) — ensure control
4. G10 (prompt eval) — the research core, probably split into multiple stories

**The gating question for this epic:** Can we define binary eval assertions for BMAD skill quality? If yes, the autoresearch pattern applies directly. If skill quality remains subjective, we need `/autoresearch:reason` (adversarial debate) instead of `/autoresearch:fix` (mechanical iteration).

---

## 9. Integration Decision Matrix

| When | What Triggers | Which Mode | What It Does | Readiness |
|------|-------------|-----------|-------------|-----------|
| After code-review | Patch findings exist | `/autoresearch:fix` | Auto-resolve D/P findings | **Near-ready** (G1+G2 needed) |
| During dev-story | Eval assertions exist | `/autoresearch:fix` | TDD-style implementation | Ready (but less valuable than manual dev for skill stories) |
| End of epic | Retrospective | `/autoresearch:learn` | Generate/update project docs | Ready (already installed) |
| End of epic | Deferred work patterns | `/autoresearch:reason` | Propose skill improvements | Ready (but needs G6 for data) |
| Pre-dev | Story created | `/autoresearch:scenario` | Edge case exploration | Ready (nice-to-have) |
| Pre-dev | Story created | `/autoresearch:predict` | Risk assessment | Ready (nice-to-have) |

---

## Sources

### Primary Sources
- [GitHub: karpathy/autoresearch](https://github.com/karpathy/autoresearch) (65K stars)
- [Fortune: 'The Karpathy Loop': 700 experiments, 2 days](https://fortune.com/2026/03/17/andrej-karpathy-loop-autonomous-ai-agents-future/)
- [VentureBeat: Karpathy's autoresearch](https://venturebeat.com/technology/andrej-karpathys-new-open-source-autoresearch-lets-you-run-hundreds-of-ai)

### Community and Integration Sources
- [MindStudio: AutoResearch Pattern Applied to Claude Code Skills](https://www.mindstudio.ai/blog/karpathy-autoresearch-pattern-claude-code-skills)
- [MindStudio: Claude Code with AutoResearch for Self-Improving Skills](https://www.mindstudio.ai/blog/claude-code-autoresearch-self-improving-skills)
- [GitHub: uditgoenka/autoresearch (Claude Code skill)](https://github.com/uditgoenka/autoresearch)
- [Addy Osmani: Self-Improving Coding Agents](https://addyosmani.com/blog/self-improving-agents/)
- [Vercel: Eval-Driven Development](https://vercel.com/blog/eval-driven-development-build-better-ai-faster)

### Academic and Technical Sources
- [Arxiv: Bilevel Autoresearch](https://arxiv.org/html/2603.23420)
- [Sakana AI: Darwin Godel Machine](https://sakana.ai/dgm/)
- [Latent Space: Autoresearch: Sparks of Recursive Self Improvement](https://www.latent.space/p/ainews-autoresearch-sparks-of-recursive)
- [DataCamp: Guide to Autoresearch](https://www.datacamp.com/tutorial/guide-to-autoresearch)
- [Autoresearch 101 Builder's Playbook](https://sidsaladi.substack.com/p/autoresearch-101-builders-playbook)

### Internal References
- `.claude/skills/autoresearch/` — installed skill with 10 modes
- `.claude/skills/create-story-with-evals/` — eval assertion generator
- `homelab-playbook/_bmad-output/implementation-artifacts/deferred-work.md` — recurring finding patterns
