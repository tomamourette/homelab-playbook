# Document Project

**Context Management** | **Agent:** Analyst (Mary) | **Model:** Gemini Pro (local) | **Cost:** $0

## When to Use

Generate or update project documentation for brownfield projects. Useful for onboarding BMAD to an existing codebase.

## Execution

Handle locally on Gemini Pro. May need read access to the workspace.

1. Scan the project structure (directories, config files, key source files)
2. Generate documentation covering:
   - **Project overview:** What this project does
   - **Directory structure:** What lives where
   - **Tech stack:** Languages, frameworks, tools
   - **How to run:** Setup, build, test commands
   - **Architecture overview:** High-level component map
   - **Key configuration:** Environment variables, config files
3. Write to `docs/project-overview.md`

## Output

A project documentation file useful for context in future BMAD sessions and for CLAUDE.md.
