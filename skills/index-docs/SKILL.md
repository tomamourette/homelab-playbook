# Index Docs

**Core Utility** | **Model:** `/model instant` (Groq) | **Cost:** $0

## When to Use

Create or update an index of all project documentation. Useful for navigating large doc sets.

## Execution

Handle locally on cheapest model. This is mechanical work.

1. Scan `docs/` directory for all markdown files
2. Generate an index with:
   - File path
   - Document title (from first heading)
   - Brief description (first paragraph or summary)
   - Last modified date
3. Write to `docs/INDEX.md`

## Output

A documentation index file for quick reference.
