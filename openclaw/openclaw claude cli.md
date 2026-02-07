# **Orchestrating Autonomous Development Environments: A Technical Analysis of OpenClaw and Claude Code Integration**

## **1\. Introduction: The Emergence of Local-First Agentic Orchestration**

The trajectory of artificial intelligence in software development has shifted rapidly from cloud-based, chat-centric paradigms toward localized, persistent, and autonomous agentic systems. This evolution is driven by a critical necessity for data privacy, reduced latency, and the ability to execute complex, long-running tasks without constant human intervention. Within this emerging landscape, two distinct technologies have risen to prominence: OpenClaw, a local-first AI operating system formerly known as Clawdbot and Moltbot 1, and Claude Code, a specialized command-line interface (CLI) optimized for agentic software engineering.3

The integration of these two systems—where OpenClaw serves as the persistent orchestrator and Claude Code functions as the specialized execution engine—represents a significant advancement in the development of "second brain" architectures. This report provides an exhaustive technical analysis of how OpenClaw can be configured to manage the Claude Code CLI for development purposes. It explores the architectural synergy between the persistent gateway model of OpenClaw and the headless execution capabilities of Claude Code, detailing the configuration protocols, security implications, and operational workflows required to establish a robust, autonomous development environment.

The core premise of this integration is the transformation of the developer’s role from a direct writer of code to a supervisor of agentic workflows. By leveraging OpenClaw’s multi-channel gateway, which maintains persistent connections to messaging platforms like Telegram and Discord 5, developers can issue high-level directives from mobile devices. These directives are then translated into specific execution commands for Claude Code, which operates directly on the local filesystem to plan, edit, test, and commit code.6 This analysis delves into the mechanisms of this "Supervisor-Worker" pattern, examining the file-based memory systems, the "AgentSkills" interface standard, and the complex security landscape defined by the potential for supply-chain attacks within agent skill repositories.

## **2\. Architectural Foundations of the Agentic Stack**

To understand the orchestration capabilities of OpenClaw over Claude Code, one must first dissect the divergent yet complementary architectures of these two systems. While both are built to interact with Large Language Models (LLMs), their operational scopes, concurrency models, and interaction surfaces differ fundamentally.

### **2.1 OpenClaw: The Persistent Gateway Daemon**

OpenClaw operates as a local gateway, a design philosophy that differentiates it from ephemeral chat interfaces. It functions as a persistent background daemon, capable of running on user hardware or within containerized environments, ensuring that the agent remains active and responsive even when the user is not directly interacting with it.1

The architecture of OpenClaw is defined by its "lane-based concurrency" model. This system separates different types of tasks into distinct execution lanes: a chat lane for immediate user interaction, a cron lane for scheduled background jobs, and sub-agent lanes for nested tool calls.1 This architectural decision is critical for orchestrating heavy workloads like software development. It ensures that a long-running compilation or refactoring task performed by a sub-agent (in this case, Claude Code) does not block the main communication channel, allowing the user to continue querying the system or issuing parallel commands.1

Data persistence in OpenClaw follows the "lobster way" philosophy—a colloquialism for its privacy-first, local-storage approach. All session history, memory, and configurations are stored as plain files on the disk, typically in JSONL or Markdown formats.1 This transparency allows for easy inspection and manual intervention, a vital feature when debugging the complex interactions between the gateway and the tools it manages. The core components include the Gateway Daemon, which manages connectivity; the Agent Runtime (nicknamed "Pi"), which serves as the cognitive engine executing prompts and scripts; and the Skill Extensions, which provide the mechanism for external tool integration.5

### **2.2 Claude Code: The Specialized Execution Engine**

In contrast to OpenClaw’s generalist, always-on nature, Claude Code is a specialized tool designed for high-fidelity software engineering tasks. Developed by Anthropic, it is optimized to function within a terminal environment, possessing deep integration with local filesystems, git repositories, and development tools.3

While Claude Code can be used interactively as a TUI (Terminal User Interface), its value in an orchestrated environment lies in its "headless mode".8 In this mode, invoked via the \-p flag, Claude Code behaves as a standard CLI utility: it accepts a prompt, performs a series of autonomous agentic turns (reasoning, tool use, execution), and returns a result before exiting.10 This stateless execution model makes it an ideal "worker" process that can be spawned, monitored, and terminated by a supervisor like OpenClaw.

The technical synergy between the two systems is evident in their contrasting strengths: OpenClaw handles the "state" (long-term memory, user preferences, communication channels), while Claude Code handles the "action" (deep code analysis, modification, and testing). Table 1 illustrates the comparative technical frameworks of these two components.

| Feature | OpenClaw (The Supervisor) | Claude Code CLI (The Worker) |
| :---- | :---- | :---- |
| **Interaction Model** | Persistent Gateway (Telegram, Discord, Web) | Ephemeral Session (Terminal, Headless) |
| **Concurrency** | Lane-based Multi-threading | Sequential Agentic Turns |
| **Primary Output** | Conversational Response, Notifications | Code Edits, Structured JSON Data |
| **State Management** | MEMORY.md, openclaw.json, jobs.json | CLAUDE.md, .claude/credentials.json |
| **Extensibility** | AgentSkills Standard (SKILL.md) | MCP Servers, Custom Tools |
| **System Access** | High-level orchestration, Cron jobs | Deep filesystem, Git, Linter integration |

Table 1: Comparative Analysis of OpenClaw and Claude Code Technical Frameworks 1

## **3\. The AgentSkills Standard: The Technical Bridge**

The fundamental mechanism enabling OpenClaw to manage Claude Code is the **AgentSkills** specification.12 This open standard, originally developed by Anthropic and adopted extensively by the OpenClaw ecosystem, defines a protocol for packaging instructions, dependencies, and scripts into portable "skills" that agents can discover and execute.12

### **3.1 Anatomy of an Orchestration Skill**

For OpenClaw to "know" how to use Claude Code, it relies on a specific skill definition, typically named coding-agent or claude-code. A skill in this ecosystem is a directory containing a mandatory SKILL.md file.14 This file uses YAML frontmatter to declare metadata and Markdown to define natural language instructions.

The structure of a skill designed to orchestrate Claude Code involves more than just a prompt; it requires defining the binary dependencies that the OpenClaw runtime must locate on the host system.

## ---

**name: coding-agent description: Orchestrates Claude Code to perform software development tasks, refactoring, and debugging. metadata: openclaw: requires: bins: \- claude \- git emoji: "👨‍💻"**

# **Instructions**

When the user requests a coding task, use the claude binary in headless mode.

Ensure you pass the user's requirements as the prompt argument using the \-p flag.

Always request output in JSON format to parse the success or failure of the operation.

This declarative format allows OpenClaw’s runtime to verify that the claude CLI is installed and available in the system path before attempting to execute the skill.12 If the binary is missing, the skill remains dormant, preventing runtime errors during execution.

### **3.2 The Execution Pipeline**

The orchestration process follows a rigorous pipeline that transforms a high-level user message into a low-level system process.

1. **Intent Recognition**: The user sends a message via a connected channel (e.g., "Refactor the login component to use hooks"). OpenClaw's internal model analyzes the intent and matches it against the descriptions in the loaded SKILL.md files.16  
2. **Context Loading**: Upon selecting the coding-agent skill, OpenClaw loads the specific instructions from the Markdown file. It may also load auxiliary scripts from a scripts/ subdirectory if complex logic is required to construct the Claude Code command.17  
3. **Process Spawning**: OpenClaw executes a shell command to spawn the Claude Code CLI. This is typically done using a subprocess wrapper that captures standard output (stdout) and standard error (stderr).12  
4. **Feedback Loop**: As Claude Code runs, it generates output. In a headless configuration, this output is captured by OpenClaw. If configured for streaming, OpenClaw can forward these updates in real-time to the user's chat interface, providing a "live" view of the coding progress.11

This interaction highlights the role of OpenClaw as a "meta-agent" or supervisor. It does not write the code itself; rather, it delegates the task to the specialized worker (Claude Code) and monitors the execution, stepping in only to report results or handle failures.7

## **4\. Environment Configuration and Deployment Protocols**

Successfully orchestrating Claude Code via OpenClaw requires a precise environmental setup. The primary challenge lies in managing the disparate file systems, permission structures, and authentication mechanisms of two independent tools running potentially within a containerized environment.

### **4.1 Containerization Strategy: Docker and Volume Mapping**

While OpenClaw can run directly on a host operating system (macOS, Linux), a Docker-based deployment is strongly recommended for security and reproducibility.19 However, running Claude Code *inside* an OpenClaw Docker container introduces complexity regarding data persistence and credential management.

The standard OpenClaw setup script (docker-setup.sh) creates specific directories on the host machine that are mounted as volumes into the container.19 For Claude Code to function correctly within this environment, its own configuration and authentication directories must also be mapped.

**Critical Volume Mounts:**

* \~/.openclaw: Stores the Gateway's configuration, memory, and installed skills.19  
* \~/openclaw/workspace: The target directory for software development tasks. This must be accessible to both the OpenClaw agent (to read/write instructions) and the Claude Code CLI (to modify code).19  
* \~/.claude: This is the most critical and often overlooked mount. Claude Code stores its persistent session history and, crucially, its authentication tokens (credentials.json) in this directory.21 Failure to mount this volume results in the agent prompting for authentication on every spawn, breaking the autonomous workflow.

A robust docker-compose.yml configuration for this integration would resemble the following structure:

YAML

services:  
  openclaw-gateway:  
    image: openclaw/gateway:latest  
    volumes:  
      \- \~/.openclaw:/root/.openclaw  
      \- \~/projects:/root/workspace  
      \- \~/.claude:/root/.claude  \# ESSENTIAL for Claude Code persistence  
    environment:  
      \- ANTHROPIC\_API\_KEY=${ANTHROPIC\_API\_KEY}  
    network\_mode: host \# Often required for local network discovery

This configuration ensures that when OpenClaw spawns a claude command inside the container, the CLI finds the existing credentials and session history, allowing it to proceed without user intervention.21

### **4.2 Authentication Management and Token Handoff**

Authentication presents a unique hurdle in headless environments. Claude Code supports two primary authentication modes: OAuth (for Claude Pro/Max subscribers) and API Key (for Claude Console users).3

**The OAuth Challenge:** The OAuth flow requires an interactive browser session to authorize the CLI. In a headless environment (like a remote VPS running OpenClaw), the CLI cannot launch a browser. The workaround involves a manual "token handoff".22

1. **Local Authentication**: The developer runs claude login on their local machine.  
2. **Token Extraction**: The generated credentials are stored in \~/.claude/credentials.json.  
3. **Transfer**: This file is securely copied to the mapped volume directory on the server (e.g., the VPS hosting OpenClaw).  
4. **Verification**: When the OpenClaw container starts, it mounts this file, allowing the internal Claude Code instance to authenticate successfully.23

**The API Key Alternative:** For purely automated environments, using an API key (Claude Console) is often more reliable as it bypasses the OAuth refresh token complexity. This can be configured by injecting the ANTHROPIC\_API\_KEY environment variable into the Docker container.21 However, users must be wary of the cost implications, as an unmonitored agent entering a loop can rapidly consume credits.19

### **4.3 Headless Mode Configuration**

To effectively "manage" Claude Code, OpenClaw must invoke it using specific flags that disable interactivity and enforce machine-readable outputs. The \-p (print) flag is the cornerstone of this integration.8

**Operational Flags for Orchestration:**

* \-p "PROMPT": Sends a single prompt to the agent and exits after completion. This turns the conversational tool into a transactional utility.10  
* \--dangerously-skip-permissions: By default, Claude Code asks for confirmation before editing files or running shell commands. In an autonomous workflow managed by OpenClaw, these prompts would cause the process to hang. This flag is essential for true autonomy but introduces significant risk, necessitating strictly sandboxed environments.27  
* \--output-format json: Forces the output into a structured JSON format, enabling OpenClaw to programmatically parse the result, check for errors, and summarize the activity for the user.27

## **5\. Operational Orchestration: Workflows and Logic**

Once the environment is configured, the operational management of Claude Code by OpenClaw relies on defining specific workflows. These workflows dictate how the Supervisor (OpenClaw) directs the Worker (Claude Code) to achieve complex development goals.

### **5.1 The Reviewer Workflow**

A common implementation is the "Reviewer Agent" workflow. In this scenario, OpenClaw is utilized to perform code reviews on demand, triggered via a mobile messaging app.30

**Workflow Logic:**

1. **Trigger**: User sends "Review the changes in src/auth.ts for security flaws" to OpenClaw via Telegram.  
2. **Translation**: OpenClaw parses the intent and maps the target file path.  
3. **Execution**: OpenClaw executes the following command:  
   claude \-p "Review src/auth.ts for security vulnerabilities. Output a JSON summary of findings." \--output-format json  
4. **Analysis**: Claude Code reads the file, consults its internal knowledge base, and generates a JSON report.  
5. **Reporting**: OpenClaw parses the JSON, formats a human-readable summary (e.g., "Found 2 critical issues: Hardcoded secret on line 12..."), and sends it back to the Telegram chat.30

This workflow leverages the "Read" capability of Claude Code without necessarily engaging its "Edit" capabilities, providing a safe entry point for agentic integration.

### **5.2 The Autonomous Builder Workflow**

More advanced scenarios involve the "Builder" workflow, where OpenClaw manages a multi-turn development session. This requires persistence of context between CLI calls.6

**Workflow Logic:**

1. **Trigger**: User requests "Add a dark mode toggle to the frontend."  
2. **Initialization**: OpenClaw checks the MEMORY.md for project context and constructs a comprehensive prompt.  
3. **Iteration 1 (Plan)**: OpenClaw runs Claude Code to generate an implementation plan.  
4. **Approval**: OpenClaw presents the plan to the user. Upon approval ("Go ahead"), it proceeds.  
5. **Iteration 2 (Execute)**: OpenClaw spawns Claude Code with the \--dangerously-skip-permissions flag to apply edits to CSS and React components.  
6. **Iteration 3 (Verify)**: OpenClaw instructs Claude Code to run the test suite (npm test) and report results.  
7. **Finalization**: If tests pass, OpenClaw uses the gh CLI (via the github-integration skill) to create a pull request.12

This workflow demonstrates the "Supervisor" role of OpenClaw, which chains together multiple discrete tools—Claude Code for editing, npm for testing, and gh for version control—into a cohesive autonomous process.6

### **5.3 Second Brain Synchronization**

A distinct but highly valuable workflow involves using Claude Code to maintain a "Second Brain" or knowledge base.31 In this setup, OpenClaw runs a nightly cron job that triggers Claude Code to analyze the day's modified files and update a central Obsidian vault or MEMORY.md file.12

This utilizes Claude Code's ability to "understand" code changes and synthesize them into natural language summaries. The orchestration here is purely automated (cron-based) rather than user-triggered, showcasing the value of OpenClaw's scheduling lanes.1

## **6\. Security Landscapes and Threat Modeling**

The capability to run shell commands, modify files, and access the network creates a massive attack surface. The integration of OpenClaw and Claude Code essentially provides "God-mode" access to the host system, necessitating a rigorous security posture.32

### **6.1 The "ClawHub" Supply Chain Vulnerability**

A critical risk vector in the OpenClaw ecosystem is the "ClawHub" marketplace. Research has identified significant supply-chain vulnerabilities where malicious skills are distributed to unsuspecting users.34

**The Malware Mechanism:**

Because a skill is simply a directory with a SKILL.md file, attackers can embed malicious commands within the Markdown instructions.

* **The Bait**: A skill might promise "Weather Updates" or "Crypto Tracking".35  
* **The Switch**: Hidden within the install instructions or execution scripts are commands that download and execute external binaries. For example, a "Quick one-liner" to test a skill might actually use curl to fetch a script that installs an SSH key into \~/.ssh/authorized\_keys.35  
* **Payloads**: Detected payloads include info-stealers like "AMOS Stealer" (Atomic macOS Stealer), which exfiltrate keychain data, browser cookies, and crypto wallets.36

The reliance on Markdown as executable code creates a "Trojan Horse" effect: the user (and the agent) reads the text as documentation, but the underlying execution engine processes it as a command. This is exacerbated when agents like OpenClaw are configured to auto-execute suggested commands found in skills.13

### **6.2 Defensive Architecture and Mitigation**

To mitigate these risks while retaining the utility of the OpenClaw-Claude Code integration, a "Defense in Depth" strategy is required.

**1\. Sandboxing and Isolation:** Running the entire OpenClaw stack within a Docker container is the first line of defense. However, standard containers are not impervious. Security-conscious deployments should utilize "rootless" Docker modes or specialized sandbox containers (like Cloudflare Sandboxes) to limit the blast radius of a compromised agent.20

**2\. Network Filtering (Egress Control):** A compromised skill often attempts to exfiltrate data (like .env files) to an attacker-controlled server. Implementing a local proxy or egress filter is crucial. Tools like Composio or simple firewall rules should be configured to allow traffic *only* to trusted API endpoints (e.g., api.anthropic.com, api.openai.com, github.com) and block all other outbound connections.39

**3\. Terminal Execution Policies:** OpenClaw provides configuration options to control the autonomy of the agent. Users should enforce a "Review Policy" for terminal execution. Even if the agent is "managing" Claude Code, the initial command to spawn the process should require explicit user approval via the chat interface, especially if it involves the \--dangerously-skip-permissions flag.40

**4\. Skill Auditing:** Users should strictly avoid installing skills from unverified authors on ClawHub. Automated tools like openclaw-skills-security-checker can be employed to scan SKILL.md files for suspicious patterns, such as encoded strings, curl | bash patterns, or references to external binaries.42

## **7\. Advanced Customization: Developing the Management Layer**

For developers whose needs exceed the pre-packaged skills, creating a custom management layer is the next step. This involves writing custom SKILL.md files that precisely define how OpenClaw should wield Claude Code.

### **7.1 Defining the Custom Skill**

To create a custom orchestration skill, one must define the directory structure and the instruction set.

**Directory Setup:**

Bash

mkdir \-p \~/.openclaw/skills/my-architect  
cd \~/.openclaw/skills/my-architect  
touch SKILL.md

**Instruction Design (SKILL.md):**

The instructions must be explicit about *how* to use Claude Code. It is not enough to say "write code." The prompt must guide Claude Code to use its internal tools effectively.

# **Architect Skill**

Use this skill when the user asks for high-level system design or codebase restructuring.

## **Operational Steps**

1. Analyze the current directory structure using ls \-R.  
2. Spawn Claude Code with the prompt: "Analyze the project architecture and propose a refactoring plan for."  
3. Use the flag \--output-format json to capture the plan.  
4. Save the plan to docs/architecture/refactor\_plan.md.  
5. Report the location of the plan to the user.

This level of granularity ensures that OpenClaw drives Claude Code deterministically.15

### **7.2 Integrating Sub-Agents and Swarms**

The flexibility of OpenClaw allows for the creation of "Swarms" where multiple Claude Code instances are spawned with different personas. A "QA Swarm" skill might spawn three parallel Claude Code processes: one to write unit tests, one to write integration tests, and one to attempt to break the code (chaos testing).41 OpenClaw manages the concurrency, ensuring that the machine's resources are not overwhelmed, and synthesizes the results from all three workers into a final report.18

## **8\. Future Trajectories: The Convergence of Interfaces**

The ecosystem surrounding OpenClaw and Claude Code is rapidly evolving toward a convergence of interfaces. The "one implementation, many interfaces" trend suggests that the distinction between a CLI agent, a chat agent, and an IDE extension is blurring.44

The **Model Context Protocol (MCP)** is emerging as the unifying standard for how these agents connect to data and tools. Future versions of OpenClaw are expected to support MCP servers natively, allowing Claude Code to access OpenClaw's persistent memory directly without relying on file-based handoffs.14 This would eliminate much of the friction associated with current "token handoff" and volume mounting workarounds.

Furthermore, the "AgentSkills" standard continues to mature. As more tools adopt this format, skills written for OpenClaw will become increasingly portable, capable of running within other environments like VS Code or proprietary agent runners.12 This interoperability reinforces the value of investing in the OpenClaw-Claude Code stack today, as the workflows developed are likely to remain relevant even as the underlying platforms shift.

## **9\. Conclusion**

The integration of OpenClaw as a manager for the Claude Code CLI offers a powerful paradigm for autonomous software development. By leveraging OpenClaw's persistent gateway architecture and Claude Code's specialized headless execution capabilities, developers can construct a "Second Brain" that works tirelessly in the background, maintaining codebases, reviewing changes, and executing complex refactors.

However, this power comes with significant responsibility. The "God-mode" access required by these tools necessitates a disciplined approach to security, including containerization, network filtering, and rigorous skill auditing. The current landscape is one of rapid innovation but also fragility; success requires not just the installation of tools but the careful orchestration of environments, permissions, and workflows.

For the modern developer, mastering this orchestration is more than a productivity hack—it is a step toward a future where the human role is elevated to that of an architect, guiding a fleet of autonomous agents that handle the implementation details. The technical path outlined in this report—from Docker volume mounts to JSON-based feedback loops—provides the blueprint for building that future today.

#### **Works cited**

1. OpenClaw: Why This “Personal AI OS” Went Viral Overnight | by Edwin Lisowski | Feb, 2026, accessed on February 6, 2026, [https://medium.com/@elisowski/openclaw-why-this-personal-ai-os-went-viral-overnight-31d668e7d2d7](https://medium.com/@elisowski/openclaw-why-this-personal-ai-os-went-viral-overnight-31d668e7d2d7)  
2. The wild rise of OpenClaw..., accessed on February 6, 2026, [https://www.youtube.com/watch?v=ssYt09bCgUY](https://www.youtube.com/watch?v=ssYt09bCgUY)  
3. Quickstart \- Claude Code Docs, accessed on February 6, 2026, [https://code.claude.com/docs/en/quickstart](https://code.claude.com/docs/en/quickstart)  
4. Claude Code overview \- Claude Code Docs, accessed on February 6, 2026, [https://code.claude.com/docs/en/overview](https://code.claude.com/docs/en/overview)  
5. Clawdbot (Moltbot) Tutorial: Self-Hosted AI Assistant with Local Memory & Automation, accessed on February 6, 2026, [https://www.growthjockey.com/blogs/clawdbot-moltbot](https://www.growthjockey.com/blogs/clawdbot-moltbot)  
6. My First Three Days with Clawdbot (now Moltbot) | by Jonathan Fulton \- Medium, accessed on February 6, 2026, [https://medium.com/jonathans-musings/my-first-three-days-with-clawdbot-now-moltbot-18835f351903](https://medium.com/jonathans-musings/my-first-three-days-with-clawdbot-now-moltbot-18835f351903)  
7. Everyone talks about Clawdbot (openClaw), but here's how it works : r/ChatGPT \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/ChatGPT/comments/1qr45nw/everyone\_talks\_about\_clawdbot\_openclaw\_but\_heres/](https://www.reddit.com/r/ChatGPT/comments/1qr45nw/everyone_talks_about_clawdbot_openclaw_but_heres/)  
8. Headless Mode Automation, accessed on February 6, 2026, [https://www.claudecode101.com/en/tutorial/advanced/headless-mode](https://www.claudecode101.com/en/tutorial/advanced/headless-mode)  
9. Run Claude Code programmatically \- Claude Code Docs, accessed on February 6, 2026, [https://code.claude.com/docs/en/headless](https://code.claude.com/docs/en/headless)  
10. Headless Mode: Unleash AI in Your CI/CD Pipeline \- DEV Community, accessed on February 6, 2026, [https://dev.to/rajeshroyal/headless-mode-unleash-ai-in-your-cicd-pipeline-1imm](https://dev.to/rajeshroyal/headless-mode-unleash-ai-in-your-cicd-pipeline-1imm)  
11. Best Practices for Claude Code, accessed on February 6, 2026, [https://code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)  
12. OpenClaw (Clawdbot) Tutorial: Control Your PC from WhatsApp | DataCamp, accessed on February 6, 2026, [https://www.datacamp.com/tutorial/moltbot-clawdbot-tutorial](https://www.datacamp.com/tutorial/moltbot-clawdbot-tutorial)  
13. From magic to malware: How OpenClaw's agent skills become an attack surface, accessed on February 6, 2026, [https://1password.com/blog/from-magic-to-malware-how-openclaws-agent-skills-become-an-attack-surface](https://1password.com/blog/from-magic-to-malware-how-openclaws-agent-skills-become-an-attack-surface)  
14. Exploring the OpenClaw Extension Ecosystem: 50+ Official Integrations Make AI Assistants All-Powerful \- Apiyi.com Blog, accessed on February 6, 2026, [https://help.apiyi.com/en/openclaw-extensions-ecosystem-guide-en.html](https://help.apiyi.com/en/openclaw-extensions-ecosystem-guide-en.html)  
15. vercel-labs/skills: The open agent skills tool \- npx skills \- GitHub, accessed on February 6, 2026, [https://github.com/vercel-labs/skills](https://github.com/vercel-labs/skills)  
16. Agent Skills: Governing Coding Agents Before They Govern Us | by Dave Patten \- Medium, accessed on February 6, 2026, [https://medium.com/@dave-patten/agent-skills-governing-coding-agents-before-they-govern-us-f458c6d0eace](https://medium.com/@dave-patten/agent-skills-governing-coding-agents-before-they-govern-us-f458c6d0eace)  
17. Simon Willison on skills, accessed on February 6, 2026, [https://simonwillison.net/tags/skills/](https://simonwillison.net/tags/skills/)  
18. Agent Zero \- A personal, organic agentic framework that grows and learns with you, accessed on February 6, 2026, [https://forum.cloudron.io/topic/14958/agent-zero-a-personal-organic-agentic-framework-that-grows-and-learns-with-you](https://forum.cloudron.io/topic/14958/agent-zero-a-personal-organic-agentic-framework-that-grows-and-learns-with-you)  
19. Running OpenClaw in Docker \- Simon Willison: TIL, accessed on February 6, 2026, [https://til.simonwillison.net/llms/openclaw-docker](https://til.simonwillison.net/llms/openclaw-docker)  
20. How to Run OpenClaw with DigitalOcean, accessed on February 6, 2026, [https://www.digitalocean.com/community/tutorials/how-to-run-openclaw](https://www.digitalocean.com/community/tutorials/how-to-run-openclaw)  
21. How to persists claude code credentials in a docker container? : r/ClaudeAI \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/ClaudeAI/comments/1ki4kjy/how\_to\_persists\_claude\_code\_credentials\_in\_a/](https://www.reddit.com/r/ClaudeAI/comments/1ki4kjy/how_to_persists_claude_code_credentials_in_a/)  
22. How to avoid re-authenticating in docker container? · Issue \#1736 · anthropics/claude-code, accessed on February 6, 2026, [https://github.com/anthropics/claude-code/issues/1736](https://github.com/anthropics/claude-code/issues/1736)  
23. Clawdbot: the AI assistant that actually messages you first, accessed on February 6, 2026, [https://www.reddit.com/r/LocalLLM/comments/1qmrwxl/clawdbot\_the\_ai\_assistant\_that\_actually\_messages/](https://www.reddit.com/r/LocalLLM/comments/1qmrwxl/clawdbot_the_ai_assistant_that_actually_messages/)  
24. The Ultimate Guide to OpenClaw (Formerly Clawdbot \-\> Moltbot) From setup and mind-blowing use cases to managing critical security risks you cannot ignore. This is the Rise of the 24/7 Proactive AI Agent Employees : r/ThinkingDeeplyAI \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/ThinkingDeeplyAI/comments/1qsoq4h/the\_ultimate\_guide\_to\_openclaw\_formerly\_clawdbot/](https://www.reddit.com/r/ThinkingDeeplyAI/comments/1qsoq4h/the_ultimate_guide_to_openclaw_formerly_clawdbot/)  
25. Configure Claude Code \- Docker Docs, accessed on February 6, 2026, [https://docs.docker.com/ai/sandboxes/claude-code/](https://docs.docker.com/ai/sandboxes/claude-code/)  
26. How to set up OpenClaw on a private server \- Hostinger, accessed on February 6, 2026, [https://www.hostinger.com/tutorials/how-to-set-up-openclaw](https://www.hostinger.com/tutorials/how-to-set-up-openclaw)  
27. CLI reference \- Claude Code Docs, accessed on February 6, 2026, [https://code.claude.com/docs/en/cli-reference](https://code.claude.com/docs/en/cli-reference)  
28. Development containers \- Claude Code Docs, accessed on February 6, 2026, [https://code.claude.com/docs/en/devcontainer](https://code.claude.com/docs/en/devcontainer)  
29. Guaranteed JSON Schema Compliance for Claude Code Output · Issue \#9058 \- GitHub, accessed on February 6, 2026, [https://github.com/anthropics/claude-code/issues/9058](https://github.com/anthropics/claude-code/issues/9058)  
30. Unleashing OpenClaw: The Ultimate Guide to Local AI Agents for Developers in 2026 \- DEV Community, accessed on February 6, 2026, [https://dev.to/mechcloud\_academy/unleashing-openclaw-the-ultimate-guide-to-local-ai-agents-for-developers-in-2026-3k0h](https://dev.to/mechcloud_academy/unleashing-openclaw-the-ultimate-guide-to-local-ai-agents-for-developers-in-2026-3k0h)  
31. I Built My Second Brain with Claude Code \+ Obsidian \+ Skills (Here's How) \- YouTube, accessed on February 6, 2026, [https://www.youtube.com/watch?v=jYMhDEzNAN0](https://www.youtube.com/watch?v=jYMhDEzNAN0)  
32. The Clawdbot Disaster Nobody's Talking About (AI Agent Takeover), accessed on February 6, 2026, [https://www.youtube.com/watch?v=N2w0vSSju4c](https://www.youtube.com/watch?v=N2w0vSSju4c)  
33. Personal AI Agents like OpenClaw Are a Security Nightmare, accessed on February 6, 2026, [https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare](https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare)  
34. OpenClaw is terrifying and the ClawHub ecosystem is already full of malware \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/cybersecurity/comments/1qwrwsh/openclaw\_is\_terrifying\_and\_the\_clawhub\_ecosystem/](https://www.reddit.com/r/cybersecurity/comments/1qwrwsh/openclaw_is_terrifying_and_the_clawhub_ecosystem/)  
35. From Automation to Infection (Part II): Reverse Shells, Semantic Worms, and Cognitive Rootkits in OpenClaw Skills \- VirusTotal Blog, accessed on February 6, 2026, [https://blog.virustotal.com/2026/02/from-automation-to-infection-part-ii.html](https://blog.virustotal.com/2026/02/from-automation-to-infection-part-ii.html)  
36. Helpful Skills or Hidden Payloads? Bitdefender Labs Dives Deep into the OpenClaw Malicious Skill Trap, accessed on February 6, 2026, [https://www.bitdefender.com/en-us/blog/labs/helpful-skills-or-hidden-payloads-bitdefender-labs-dives-deep-into-the-openclaw-malicious-skill-trap](https://www.bitdefender.com/en-us/blog/labs/helpful-skills-or-hidden-payloads-bitdefender-labs-dives-deep-into-the-openclaw-malicious-skill-trap)  
37. Weaponized OpenClaw Skills Deliver Atomic Stealer Malware, accessed on February 6, 2026, [https://socprime.com/active-threats/openclaw-ai-agent-weaponized/](https://socprime.com/active-threats/openclaw-ai-agent-weaponized/)  
38. cloudflare/moltworker: Run OpenClaw, (formerly Moltbot, formerly Clawdbot) on Cloudflare Workers \- GitHub, accessed on February 6, 2026, [https://github.com/cloudflare/moltworker](https://github.com/cloudflare/moltworker)  
39. How to secure OpenClaw (formerly Moltbot / Clawdbot): Docker hardening, credential isolation, and Composio controls, accessed on February 6, 2026, [https://composio.dev/blog/secure-openclaw-moltbot-clawdbot-setup](https://composio.dev/blog/secure-openclaw-moltbot-clawdbot-setup)  
40. Google Antigravity and Gemini 3: A New Era of Agentic Development \- Medium, accessed on February 6, 2026, [https://medium.com/@vfcarida/google-antigravity-and-gemini-3-a-new-era-of-agentic-development-f952ffe93b19](https://medium.com/@vfcarida/google-antigravity-and-gemini-3-a-new-era-of-agentic-development-f952ffe93b19)  
41. Honestly guys, is OpenClaw actually practically useful? : r/ClaudeAI \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/ClaudeAI/comments/1qx955i/honestly\_guys\_is\_openclaw\_actually\_practically/](https://www.reddit.com/r/ClaudeAI/comments/1qx955i/honestly_guys_is_openclaw_actually_practically/)  
42. awesome-openclaw-skills/README.md at main \- GitHub, accessed on February 6, 2026, [https://github.com/VoltAgent/awesome-openclaw-skills/blob/main/README.md](https://github.com/VoltAgent/awesome-openclaw-skills/blob/main/README.md)  
43. From Automation to Infection: How OpenClaw AI Agent Skills Are Being Weaponized \- VirusTotal Blog, accessed on February 6, 2026, [https://blog.virustotal.com/2026/02/from-automation-to-infection-how.html](https://blog.virustotal.com/2026/02/from-automation-to-infection-how.html)  
44. OpenClaw Skill is Live \- You.com, accessed on February 6, 2026, [https://you.com/resources/openclaw-integration](https://you.com/resources/openclaw-integration)