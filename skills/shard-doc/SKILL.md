# Shard Document

**Core Utility** | **Model:** `/model instant` (Groq) | **Cost:** $0

## When to Use

Split a large document into smaller, manageable chunks. Useful when a document exceeds context window limits or needs to be processed in parts.

## Execution

Handle locally on cheapest model. This is mechanical work.

1. Read the large document
2. Split by logical sections (headings, chapters)
3. Write each shard as a separate file: `docs/shards/original-name-part-NNN.md`
4. Create an index file listing all shards with their section titles

## Output

Multiple smaller files, each containing a logical section of the original. Plus an index file.
