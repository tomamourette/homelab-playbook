# Create Epics and Stories

**Phase:** 3 — Solutioning | **Agent:** PM (John) | **Model:** Gemini Pro (local) | **Cost:** $0

## When to Use

Break the PRD and architecture into epics and user stories. This is the bridge between architecture and implementation.

## Prerequisites

- PRD must exist
- Architecture document should exist (or be in progress)

## Execution

Handle locally on Gemini Pro.

1. Read the PRD and architecture document
2. Create epics (large feature groups) from the PRD's functional requirements
3. For each epic, create user stories following the format:
   - **Title:** Short descriptive name
   - **As a** [user], **I want** [capability], **so that** [benefit]
   - **Acceptance criteria:** Specific, testable conditions
   - **Technical notes:** References to architecture decisions, dependencies
   - **Estimated complexity:** S/M/L
4. Write epics to `docs/epics/` directory, one file per epic
5. Write stories to `docs/stories/` directory, one file per story
6. Create an index file at `docs/epics/index.md` listing all epics and their stories

## Output

Epic and story files in the workspace. These feed into sprint planning (Phase 4).
