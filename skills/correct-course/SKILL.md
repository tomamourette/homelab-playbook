# Correct Course

**Phase:** 4 — Implementation | **Agent:** Scrum Master (Bob) | **Model:** `/model reason` (DeepSeek R1) | **Cost:** ~$0.02-0.05
**Frequency:** Exception-only

## When to Use

Only triggered when implementation reveals an issue, limitation, or improvement that would alter the architecture or stories. This is NOT a routine workflow — it's the exception path.

## Trigger Flow

```
Discover issue during dev → Research (Phase 1: technical-research or domain-research) → Correct Course → Update architecture/stories
```

Almost always preceded by a research step. Don't correct course without understanding the problem first.

## Execution

Handle locally. Use `/model reason` (DeepSeek R1) for impact analysis.

1. Document the issue discovered during implementation:
   - What was found?
   - Why does it change the plan?
   - What's the impact on architecture/stories?
2. Analyze the impact:
   - Which architecture decisions are affected?
   - Which stories need updating?
   - Is a new epic needed?
   - Any new technical risks?
3. Propose corrections:
   - Architecture changes needed
   - Story modifications or additions
   - Sprint plan adjustments
4. Present the correction proposal to the user for approval
5. After approval, update the affected documents

## Output

A change proposal with impact analysis. User must approve before documents are modified. Then update architecture and stories accordingly.
