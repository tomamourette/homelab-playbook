---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'WhatsApp auto-responder via Hermes agent'
research_goals: 'Determine technical feasibility of Hermes agent receiving WhatsApp messages and responding on behalf of the user — covering WhatsApp bridge options, API access, self-hosted solutions, and full pipeline architecture'
user_name: 'tomamourette'
date: '2026-04-14'
web_research_enabled: true
source_verification: true
---

# WhatsApp Auto-Responder via Hermes Agent: Technical Feasibility Research

**Date:** 2026-04-14
**Author:** tomamourette
**Research Type:** technical

---

## Executive Summary

This research confirms that building a WhatsApp auto-responder powered by Hermes agent is **technically feasible** and can be deployed entirely self-hosted on the existing homelab infrastructure. The recommended architecture uses **Evolution API v2** as a Docker-native WhatsApp bridge, delivering incoming messages via webhook to a **FastAPI-based Hermes skill** that orchestrates Claude API responses. Total new resource cost is ~512MB RAM in a dedicated LXC container, with an estimated $1-5/month for Claude API usage.

The use of a **WhatsApp Business account** significantly improves the risk profile. WhatsApp's January 2026 policy update bans general-purpose AI chatbots but explicitly permits structured auto-reply bots for support and task-specific responses. By framing the responder as "Tom's assistant" with clear boundaries (reply-only, no unsolicited outreach, task-specific), the system operates within policy. The primary residual risk is that Evolution API uses an unofficial protocol (Baileys) — while this is a widely-used pattern with an active community, it technically violates WhatsApp ToS and carries a non-zero ban risk.

**Key findings:**
- Evolution API is the most deployment-ready bridge option (Docker, REST, webhooks, built-in AI integrations)
- Multiple WhatsApp MCP servers exist for deeper Hermes integration (read history, search contacts)
- The full pipeline (receive → classify → context load → AI generate → throttle → reply → store) can be built in ~5 days
- Conversation state management via Omega Memory provides cross-session context recall

**Verdict: Go.** The project is viable as a homelab deployment with manageable risk.

---

## Table of Contents

1. [Technical Research Scope Confirmation](#technical-research-scope-confirmation)
2. [Technology Stack Analysis](#technology-stack-analysis)
   - WhatsApp Access Methods (3 tiers)
   - Bridge Approach: Matrix + mautrix-whatsapp
   - Container & Deployment Stack
   - ToS & Ban Risk Assessment
3. [Integration Patterns Analysis](#integration-patterns-analysis)
   - Architecture Option A: Evolution API + Webhook (recommended)
   - Architecture Option B: WhatsApp MCP Server
   - Architecture Option C: n8n Middleware
   - Architecture Option D: Matrix Bridge
   - Communication Protocols
   - Security Considerations
4. [Architectural Patterns and Design](#architectural-patterns-and-design)
   - Event-Driven Pipeline Architecture
   - Deployment Topology on Proxmox
   - Conversation State Management
   - Rate Limiting and Throttling
   - Message Processing Pipeline
   - Failure Modes and Resilience
5. [Implementation Approaches](#implementation-approaches-and-technology-adoption)
   - Phase 1: Deploy Evolution API
   - Phase 2: Build Webhook Handler
   - Phase 3: Wire Into Hermes
   - Phase 4: System Prompt Engineering
   - Phase 5: Testing and Hardening
   - Cost Analysis and Risk Mitigation
6. [Research Synthesis and Conclusions](#research-synthesis-and-conclusions)

---

## Technical Research Scope Confirmation

**Research Topic:** WhatsApp auto-responder via Hermes agent
**Research Goals:** Determine technical feasibility of Hermes agent receiving WhatsApp messages and responding on behalf of the user — covering WhatsApp bridge options, API access, self-hosted solutions, and full pipeline architecture

**Technical Research Scope:**

- Architecture Analysis — bridge protocols, message routing, AI response pipeline
- Implementation Approaches — self-hosted bridge libraries, webhook patterns
- Technology Stack — bridge engines, container deployment, MCP integration
- Integration Patterns — webhook/event-driven message flow, Hermes skill design
- Feasibility & Constraints — ToS, ban risk, encryption, personal vs business accounts

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information

**Scope Confirmed:** 2026-04-14

---

## Technology Stack Analysis

### WhatsApp Access Methods — Three Tiers

There are three distinct ways to programmatically interact with WhatsApp. Each carries different trade-offs for a self-hosted homelab scenario.

#### Tier 1: Official WhatsApp Business API (Cloud API)

Meta's official route. Hosted by Meta, accessed via REST endpoints.

- **Requires**: Meta Business account, verified business, BSP (Business Solution Provider) or direct API access
- **Designed for**: Business-to-customer messaging (support, notifications, order tracking)
- **Personal account**: **Not supported** — this is business-only
- **On-premise option**: Meta deprecated the on-premise WhatsApp Business API; migration to Cloud API is being pushed
- **Cost**: Per-conversation pricing via Meta
- **AI policy (Jan 2026)**: Meta now **bans general-purpose AI chatbots** on the Business Platform. Structured bots for support/sales/notifications are still allowed, but open-ended assistant-style AI (ChatGPT-style) is explicitly prohibited

_Confidence: HIGH — official Meta documentation and multiple corroborating sources_
_Sources: [WhatsApp Business Platform](https://business.whatsapp.com/products/business-platform), [WhatsApp On-Premises API (deprecated)](https://www.postman.com/meta/whatsapp-business-platform/documentation/vdi189b/whatsapp-on-premises-api-deprecated), [WhatsApp 2026 AI Policy Explained](https://respond.io/blog/whatsapp-general-purpose-chatbots-ban), [TechCrunch — WhatsApp bars general-purpose chatbots](https://techcrunch.com/2025/10/18/whatssapp-changes-its-terms-to-bar-general-purpose-chatbots-from-its-platform/)_

#### Tier 2: Unofficial Libraries (Baileys, whatsapp-web.js)

Reverse-engineered from WhatsApp Web's protocol. Self-hosted, no Meta approval needed. Works with personal accounts.

**Baileys** (TypeScript/Node.js):
- Uses WhatsApp Web's WebSocket protocol directly — no headless browser
- Lightweight, actively maintained (WhiskeySockets/Baileys)
- Supports sending/receiving messages, media, groups, presence
- Multi-device support via WhatsApp's linked devices feature

**whatsapp-web.js** (Node.js):
- Wraps a headless Chromium browser running WhatsApp Web
- Heavier resource footprint than Baileys
- Simpler API for basic use cases

**WPPConnect** (Node.js):
- Multi-session handling, message scheduling, webhook notifications
- Good for multi-account scenarios

**Key risk**: These violate WhatsApp ToS. Ban detection is **actively enforced** — even low-volume reply-only usage has triggered account warnings and bans in 2025. An anti-ban middleware (baileys-antiban) exists but offers no guarantees.

_Confidence: HIGH on capabilities, HIGH on ban risk_
_Sources: [Baileys docs](https://baileys.wiki/docs/intro/), [Baileys ban issues](https://github.com/WhiskeySockets/Baileys/issues/1869), [whatsmeow risk warning](https://github.com/tulir/whatsmeow/issues/810), [baileys-antiban](https://github.com/kobie3717/baileys-antiban)_

#### Tier 3: Self-Hosted API Wrappers (Evolution API, MultiWA, Whatomate)

These wrap Baileys/whatsmeow into production-ready REST APIs with Docker deployment.

**Evolution API** (most mature):
- Open-source, Docker-ready (PostgreSQL + Redis)
- RESTful API with webhook-based event delivery
- Built-in integrations: Typebot, Chatwoot, Dify, **OpenAI**, RabbitMQ, S3
- Supports WhatsApp, Instagram DM, Facebook Messenger
- QR code pairing for personal account linking
- Active community, frequent updates (2025-2026)

**MultiWA**:
- Pluggable engine adapters (switch between Baileys and whatsapp-web.js)
- Unified messaging API across engines

**Whatomate** (Go):
- Single binary, zero dependencies, Vue.js UI
- No per-message fees

_Confidence: HIGH — active GitHub repos, Docker Hub images, community documentation_
_Sources: [Evolution API GitHub](https://github.com/EvolutionAPI/evolution-api), [Evolution API on Docker](https://hub.docker.com/r/atendai/evolution-api), [MultiWA GitHub](https://github.com/ribato22/MultiWA), [Whatomate](https://whatomate.io/), [FreeCodeCamp Evolution API tutorial](https://www.freecodecamp.org/news/how-to-build-and-deploy-a-production-ready-whatsapp-bot/)_

### Bridge Approach: Matrix + mautrix-whatsapp

An alternative architecture routes WhatsApp through the Matrix protocol via a bridge.

**mautrix-whatsapp**:
- Puppeting bridge: connects WhatsApp Web multi-device API to a Matrix homeserver
- Written in Go, uses whatsmeow library internally
- Docker deployment available
- Requires: Matrix homeserver (Synapse), PostgreSQL 16+, WhatsApp on a phone
- Messages appear in Matrix rooms; you can read/reply from any Matrix client
- Hermes could interact via Matrix API instead of directly with WhatsApp

**Trade-off**: Adds a full Matrix homeserver to the stack (Synapse is resource-hungry). More moving parts, but provides protocol-level abstraction and a cleaner integration surface.

_Confidence: HIGH — well-documented, actively maintained_
_Sources: [mautrix-whatsapp docs](https://docs.mau.fi/bridges/go/setup.html?bridge=whatsapp), [mautrix-whatsapp GitHub](https://github.com/mautrix/whatsapp), [Matrix WhatsApp Bridge docs](https://matrixdocs.github.io/docs/bridges/whatsapp)_

### Container & Deployment Stack

All options are Docker-native and fit your Proxmox/LXC homelab:

| Component | Image/Tool | Resources |
|-----------|-----------|-----------|
| Evolution API | `atendai/evolution-api` | ~256MB RAM |
| PostgreSQL | `postgres:17` | ~128MB RAM |
| Redis | `redis:8` | ~64MB RAM |
| Webhook receiver (Hermes) | Custom / MCP skill | Minimal |
| **Total** | | **~500MB RAM** |

The Matrix approach adds Synapse (~512MB-1GB RAM) + mautrix-whatsapp (~64MB RAM), roughly doubling the footprint.

### WhatsApp ToS & Ban Risk Assessment

| Factor | Risk Level | Detail |
|--------|-----------|--------|
| Using unofficial API (Baileys/whatsmeow) | **HIGH** | Violates ToS, actively detected |
| Auto-replying to incoming messages | **MEDIUM-HIGH** | Even low-volume reply-only bots triggered bans in 2025 |
| Running on personal account | **HIGH** | No business verification = easier to ban |
| Using official Business API with AI | **MEDIUM** | Allowed for structured bots, banned for general-purpose AI since Jan 2026 |
| Anti-ban middleware | **LOW mitigation** | Exists but no guarantees; WhatsApp updates detection regularly |
| Account age & history | **Variable** | Fresh numbers get banned faster; established accounts have more runway |

**Bottom line (updated — Business account)**: With a WhatsApp Business account, the official Cloud API becomes available and the ToS picture improves. General-purpose AI chatbots are banned since Jan 2026, but **structured auto-reply bots for support, notifications, and task-specific responses are explicitly allowed**. The key constraint is framing the AI as a structured assistant, not an open-ended chatbot. The unofficial API route (Baileys/Evolution API) also works with business accounts and may offer more flexibility for personal-use automation where Meta's policy enforcement is lighter.

---

## Integration Patterns Analysis

### Architecture Option A: Evolution API + Webhook → Hermes (Recommended)

The most direct path. Evolution API wraps Baileys into a Docker-deployable REST server with webhook delivery.

**Message flow:**

```
WhatsApp (Business) → Evolution API (Docker) → Webhook POST → Hermes HTTP Skill → Claude API → Evolution API send → WhatsApp reply
```

**How it works:**

1. **Evolution API** connects to your WhatsApp Business account via QR code pairing (linked device)
2. Incoming messages trigger a `MESSAGES_UPSERT` webhook event
3. Webhook payload contains sender JID (`remoteJid`), message text (`message.conversation` or `message.extendedTextMessage.text`), and metadata
4. **Hermes** receives the webhook via an HTTP listener skill, extracts the message, and invokes Claude for a response
5. Hermes calls Evolution API's `POST /message/sendText/{instance}` to reply

**Evolution API webhook payload structure:**
```json
{
  "event": "messages.upsert",
  "instance": "hermes-wa",
  "data": {
    "key": {
      "remoteJid": "31612345678@s.whatsapp.net",
      "fromMe": false,
      "id": "MSG_ID"
    },
    "message": {
      "conversation": "Hey, can you check the server status?"
    }
  }
}
```

**Evolution API also has built-in OpenAI integration** — you can configure it to auto-reply using the `/openai/create/{instance}` endpoint with trigger-based activation, bypassing the need for a custom webhook handler entirely. However, wiring through Hermes gives you control over prompt engineering, context injection from Omega memory, and routing logic.

_Confidence: HIGH — documented API, active community, Docker-ready_
_Sources: [Evolution API Webhooks](https://doc.evolution-api.com/v2/en/configuration/webhooks), [Evolution API OpenAI Integration](https://doc.evolution-api.com/v2/en/integrations/openai), [Evolution API Chatbot Architecture](https://deepwiki.com/EvolutionAPI/evolution-api/6.1-chatbot-architecture-and-sessions)_

### Architecture Option B: WhatsApp MCP Server → Claude/Hermes

Multiple open-source MCP servers exist that bridge WhatsApp directly into Claude's tool ecosystem.

**Notable implementations:**

| Project | Language | Transport | Notes |
|---------|----------|-----------|-------|
| [lharries/whatsapp-mcp](https://github.com/lharries/whatsapp-mcp) | Python | stdio | SQLite message store, personal account, search/read/send |
| [jlucaso1/whatsapp-mcp-ts](https://github.com/jlucaso1/whatsapp-mcp-ts) | TypeScript (Baileys) | stdio | Direct Baileys integration, local auth cache |
| [msaelices/whatsapp-mcp-server](https://github.com/msaelices/whatsapp-mcp-server) | Python | HTTP/WS | HTTP + WebSocket transport, suitable for remote agents |
| [ericporres/whatsapp-mcp-server](https://github.com/ericporres/whatsapp-mcp-server) | Node.js | stdio + HTTP | Group chat focus, chat intelligence processor |

**Message flow:**
```
WhatsApp (Business) → WhatsApp MCP Server → MCP tools (read/send) → Hermes agent → Claude API → MCP send_message tool → WhatsApp reply
```

**Key advantage**: Hermes already speaks MCP natively. A WhatsApp MCP server would give Hermes `search_messages`, `read_conversation`, `send_message`, and `list_contacts` tools — no custom webhook handler needed.

**Key limitation**: Most MCP servers are pull-based (Hermes polls or queries), not push-based (webhook). For auto-responding, you'd need either a polling cron job or a hybrid approach where an event listener triggers Hermes.

_Confidence: HIGH on existence, MEDIUM on production-readiness (community projects, varying maturity)_
_Sources: [whatsapp-mcp GitHub](https://github.com/lharries/whatsapp-mcp), [whatsapp-mcp-ts GitHub](https://github.com/jlucaso1/whatsapp-mcp-ts), [Composio WhatsApp MCP](https://composio.dev/toolkits/whatsapp/framework/claude-code)_

### Architecture Option C: n8n / Workflow Engine as Middleware

Self-hosted n8n acts as the orchestration layer between WhatsApp and AI.

**Message flow:**
```
WhatsApp → Evolution API webhook → n8n workflow → Claude/OpenAI node → n8n → Evolution API send → WhatsApp reply
```

**Advantages:**
- Visual workflow builder — no code for the routing logic
- Built-in nodes for WhatsApp Business Cloud, OpenAI, and many other services
- Chat memory via Supabase/Postgres integration
- Handles message normalization, media transcription (Whisper), and branching logic
- Templates exist: RAG chatbot, voice note transcription, customer support

**Trade-off**: Adds n8n (~512MB RAM) to the stack. More suited if you want to expand beyond WhatsApp into multi-channel automation later.

_Confidence: HIGH — well-documented workflows, active template library_
_Sources: [n8n WhatsApp AI chatbot](https://n8n.io/workflows/2845-complete-business-whatsapp-ai-powered-rag-chatbot-using-openai/), [n8n WhatsApp auto-reply](https://n8n.io/workflows/2466-respond-to-whatsapp-messages-with-ai-like-a-pro/), [Building WhatsApp AI Agents with n8n](https://www.bitcot.com/building-custom-whatsapp-ai-agents-using-n8n-and-openai/)_

### Architecture Option D: Matrix Bridge (mautrix-whatsapp)

Route WhatsApp through Matrix protocol, interact via Matrix API.

**Message flow:**
```
WhatsApp → mautrix-whatsapp bridge → Synapse (Matrix) → Matrix bot / MCP → Hermes → Claude → Matrix send → bridge → WhatsApp reply
```

**Trade-off**: Heaviest footprint (~1.5GB RAM total). Best if you already run Matrix or want a unified messaging layer across multiple platforms. Overkill for WhatsApp-only.

_Confidence: HIGH on technical feasibility, LOW on practicality for this use case_

### Communication Protocols

| Protocol | Used By | Pattern |
|----------|---------|---------|
| WebSocket | Baileys/Evolution API ↔ WhatsApp servers | Persistent connection, real-time message delivery |
| HTTP REST | Evolution API endpoints, MCP HTTP transport | Request/response for send/config/query operations |
| Webhook (HTTP POST) | Evolution API → Hermes | Event-driven push notification on incoming messages |
| MCP (stdio/SSE) | WhatsApp MCP servers → Claude/Hermes | Tool-based interaction (search, read, send) |
| Signal Protocol | WhatsApp end-to-end encryption | Messages encrypted client-to-client; bridge decrypts at linked device level |

### Security Considerations

- **End-to-end encryption**: WhatsApp uses Signal Protocol. The bridge (Baileys/Evolution API) acts as a linked device and decrypts messages locally. Messages are in plaintext within your infrastructure.
- **API key storage**: Evolution API key and any OpenAI/Claude keys must be stored securely — use Vault or environment variables, never in config files
- **Network isolation**: Evolution API should not be exposed to the internet; keep webhook delivery on a private Docker network
- **Message logging**: Evolution API + PostgreSQL stores message history. Consider retention policies and encryption at rest.

### Revised Risk Assessment (Business Account)

| Factor | Risk Level | Detail |
|--------|-----------|--------|
| Using official Business Cloud API | **LOW** | Designed for this, ToS-compliant |
| Using unofficial API (Baileys) with business account | **MEDIUM** | Still violates ToS, but enforcement is lighter on business accounts |
| Structured auto-reply bot (support/task-specific) | **LOW** | Explicitly allowed under Jan 2026 policy |
| General-purpose AI chatbot on Business API | **HIGH** | Explicitly banned since Jan 2026 |
| Self-hosted Evolution API with business account | **MEDIUM-LOW** | Common pattern, large community, manageable risk |

_Sources: [Meta AI policy explained](https://respond.io/blog/whatsapp-general-purpose-chatbots-ban), [MEF WhatsApp AI ban analysis](https://mobileecosystemforum.com/2025/12/01/metas-whatsapp-ai-chatbot-ban/)_

---

## Architectural Patterns and Design

### Recommended System Architecture: Event-Driven Pipeline

For your homelab (Proxmox, LXC containers, Docker stacks), the recommended architecture is an **event-driven pipeline** with Evolution API as the WhatsApp gateway and Hermes as the AI orchestrator.

```
┌─────────────────────────────────────────────────────────────┐
│  ct-docker-01 (or dedicated LXC)                            │
│                                                             │
│  ┌──────────────┐   webhook    ┌──────────────────────┐     │
│  │ Evolution API │───(POST)───▶│ Hermes Webhook Skill │     │
│  │   (Baileys)   │             │  - extract message    │     │
│  │   port 8080   │◀──(REST)───│  - classify intent    │     │
│  └──────┬───────┘   sendText  │  - invoke Claude API  │     │
│         │                      │  - format reply       │     │
│         │                      └──────────┬───────────┘     │
│  ┌──────┴───────┐              ┌──────────┴───────────┐     │
│  │  PostgreSQL   │              │   Omega Memory        │     │
│  │ (msg history) │              │ (conversation context)│     │
│  └──────────────┘              └──────────────────────┘     │
│         │                                                    │
│  ┌──────┴───────┐                                           │
│  │    Redis      │                                           │
│  │  (sessions)   │                                           │
│  └──────────────┘                                           │
│                                                             │
│  ┌──────────────┐                                           │
│  │   Traefik     │  (reverse proxy, internal only)          │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

**Design principles:**
- **All traffic stays internal** — Evolution API and webhook listener communicate over Docker bridge network. No public exposure.
- **Event-driven** — Evolution API pushes messages via webhook; Hermes doesn't poll.
- **Stateless message handler** — each webhook invocation is independent. Conversation state lives in Omega Memory, not in the handler.
- **Separation of concerns** — Evolution API handles WhatsApp protocol, Hermes handles AI logic, PostgreSQL handles persistence.

_Sources: [Evolution API Docker deployment](https://doc.evolution-api.com/v2/en/install/docker), [Evolution API architecture](https://deepwiki.com/EvolutionAPI/evolution-api/1.2-installation-and-deployment)_

### Deployment Topology on Proxmox

Two viable approaches for your existing infrastructure:

**Option 1: Add to existing ct-docker-01 stack**
- Simplest — add Evolution API, PostgreSQL, and Redis as services in an existing docker-compose
- Shares the Docker host with your other stacks (Traefik, monitoring, etc.)
- Risk: resource contention if the container is already loaded

**Option 2: Dedicated LXC container (ct-whatsapp or ct-hermes-wa)**
- Clean isolation, dedicated resources (~1GB RAM, 1 vCPU)
- Own Docker daemon, own compose stack
- Easier to snapshot/backup/destroy independently
- Fits your pattern of purpose-specific containers (ct-media-01, ct-sparkle-cps, etc.)

**Recommendation**: Option 2 — a dedicated LXC keeps the WhatsApp bridge isolated, which matters because an Evolution API crash or WhatsApp session drop shouldn't affect your other services.

### Conversation State Management

The AI auto-responder needs conversation context to give coherent multi-turn replies. Two patterns:

**Pattern A: Omega Memory (recommended for Hermes)**
- Hermes already has Omega integration (Epic 2, done)
- Store conversation turns keyed by WhatsApp JID + timestamp
- On each incoming message, retrieve last N turns from Omega to build prompt context
- Namespace: `whatsapp-conversations`
- TTL: 24-48 hours (conversations are ephemeral)

**Pattern B: Evolution API's built-in session management**
- Evolution API's chatbot architecture tracks sessions per contact
- Sessions auto-expire after configurable idle timeout
- Simpler but less flexible — no cross-channel context, no integration with your broader knowledge base

**Pattern A+B hybrid**: Use Evolution API sessions for short-term state (current conversation window) and Omega for long-term context (who is this contact, what did we discuss last week).

_Sources: [Evolution API chatbot sessions](https://deepwiki.com/EvolutionAPI/evolution-api/6.1-chatbot-architecture-and-sessions), [AWS WhatsApp AI best practices](https://aws.amazon.com/blogs/messaging-and-targeting/best-practices-for-building-high-performance-whatsapp-ai-assistant-using-aws/)_

### Rate Limiting and Throttling Design

WhatsApp enforces rate limits and monitors for robotic behaviour. Your architecture must respect these:

| Constraint | Limit | Mitigation |
|-----------|-------|------------|
| API calls per second | 20-50 TPS | Rate limiter in webhook handler |
| Message pacing | 3-8s between messages (human-like) | Randomized delay before reply |
| 24-hour messaging window | Can only message users who messaged first (within 24h) | Auto-reply only — never initiate |
| Quality rating | Block/report ratio monitored by Meta | Only reply to incoming messages, keep responses relevant |
| Messaging capacity tiers | Depends on quality rating | Start conservative, let capacity grow organically |

**Critical design rule**: The bot should **only respond to incoming messages**, never initiate outbound messages unsolicited. This keeps you within WhatsApp's customer-service window and avoids the quality rating penalties that come with outbound marketing.

_Sources: [WhatsApp API rate limits](https://www.chatarchitect.com/news/whatsapp-api-rate-limits-what-you-need-to-know-before-you-scale), [WhatsApp messaging limits](https://developers.facebook.com/docs/whatsapp/messaging-limits/), [WhatsApp rate limits scaling guide](https://wasenderapi.com/blog/whatsapp-api-rate-limits-explained-how-to-scale-messaging-safely-in-2025)_

### Message Processing Pipeline

```
Incoming webhook (MESSAGES_UPSERT)
    │
    ▼
1. FILTER: Skip if fromMe=true (don't reply to own messages)
    │
    ▼
2. EXTRACT: Parse sender JID, message type, text content
    │
    ▼
3. CLASSIFY: Determine message intent (question, greeting, media, etc.)
    │         If media (audio/image): transcribe via Whisper first
    │
    ▼
4. CONTEXT: Load conversation history from Omega (last N turns)
    │         Load contact profile if available
    │
    ▼
5. GENERATE: Call Claude API with system prompt + context + message
    │         System prompt defines persona, response style, boundaries
    │
    ▼
6. THROTTLE: Apply randomized delay (3-8s) to mimic human timing
    │
    ▼
7. REPLY: POST to Evolution API sendText endpoint
    │
    ▼
8. STORE: Save turn to Omega Memory (sender, message, reply, timestamp)
```

### Security Architecture

| Layer | Control |
|-------|---------|
| Network | Evolution API on internal Docker network only; no port exposure to host |
| Authentication | Evolution API key stored in Vault / env var; Claude API key in Vault |
| Encryption | WhatsApp messages E2E encrypted (Signal Protocol); decrypted locally by linked device |
| Data at rest | PostgreSQL encryption for message history; Omega stores in encrypted namespace |
| Access control | Hermes webhook endpoint only accepts requests from Evolution API container IP |
| Logging | Audit log of all AI responses for review; PII-aware log redaction |

### Failure Modes and Resilience

| Failure | Impact | Mitigation |
|---------|--------|------------|
| Evolution API crash | Messages queue in WhatsApp; delivered on reconnect | Docker restart policy: `always`; health check + alerting |
| WhatsApp session drop | QR re-pairing needed | Monitor connection status via Evolution API `/instance/connectionState`; alert on disconnect |
| Claude API timeout | No reply sent | Retry with exponential backoff; fallback to canned response ("I'll get back to you shortly") |
| Hermes webhook down | Evolution API retries webhook delivery | Configure Evolution API retry policy; dead letter queue |
| PostgreSQL down | No message persistence | Redis as fallback session store; Evolution API continues operating |

_Sources: [Evolution API Docker docs](https://doc.evolution-api.com/v2/en/install/docker), [Coolify Evolution API](https://coolify.io/docs/services/evolution-api)_

---

## Implementation Approaches and Technology Adoption

### Step-by-Step Implementation Roadmap

#### Phase 1: Deploy Evolution API (Day 1)

**1. Create dedicated LXC container**
```bash
# On Proxmox host — create LXC for WhatsApp bridge
pct create 153 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname ct-whatsapp \
  --cores 1 --memory 1024 --swap 512 \
  --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.50.153/24,gw=192.168.50.1 \
  --features nesting=1
```

**2. Install Docker and deploy Evolution API stack**

```yaml
# docker-compose.yaml
version: '3.9'
services:
  evolution-api:
    container_name: evolution_api
    image: atendai/evolution-api:v2
    restart: always
    ports:
      - "8080:8080"
    environment:
      - AUTHENTICATION_API_KEY=${EVO_API_KEY}
      - DATABASE_ENABLED=true
      - DATABASE_PROVIDER=postgresql
      - DATABASE_CONNECTION_URI=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/evolution
      - DATABASE_SAVE_DATA_NEW_MESSAGE=true
      - DATABASE_SAVE_DATA_CONTACTS=true
      - DATABASE_SAVE_DATA_CHATS=true
      - CACHE_REDIS_ENABLED=true
      - CACHE_REDIS_URI=redis://redis:6379/1
      - SERVER_URL=http://evolution-api:8080
      - DEL_INSTANCE=false
    depends_on:
      - postgres
      - redis
    networks:
      - wa-bridge

  postgres:
    container_name: evo_postgres
    image: postgres:17
    restart: always
    environment:
      - POSTGRES_DB=evolution
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    networks:
      - wa-bridge

  redis:
    container_name: evo_redis
    image: redis:8-alpine
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - wa-bridge

volumes:
  pg_data:
  redis_data:

networks:
  wa-bridge:
    driver: bridge
```

**3. Create instance and pair WhatsApp Business**

```bash
# Create a new WhatsApp instance
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: ${EVO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "hermes-wa",
    "integration": "WHATSAPP-BAILEYS",
    "webhook": {
      "url": "http://hermes-webhook:5000/webhook/whatsapp",
      "webhookByEvents": false,
      "webhookBase64": false,
      "events": ["MESSAGES_UPSERT"]
    }
  }'
# Response includes QR code in base64 — scan with WhatsApp Business app
```

_Sources: [Evolution API Docker docs](https://doc.evolution-api.com/v2/en/install/docker), [Evolution API instance creation](https://docs.evoapicloud.com/instances/overview), [Evolution API GitHub docker-compose](https://github.com/EvolutionAPI/evolution-api/blob/main/docker-compose.yaml)_

#### Phase 2: Build Hermes Webhook Skill (Day 2-3)

The webhook receiver is a lightweight HTTP server that Hermes runs as a skill. It receives Evolution API webhook payloads and orchestrates the AI response.

**Pseudocode for the webhook handler:**

```python
# hermes-wa-responder skill (FastAPI-based)

@app.post("/webhook/whatsapp")
async def handle_whatsapp_webhook(payload: dict):
    event = payload.get("event")
    if event != "messages.upsert":
        return {"status": "ignored"}

    data = payload["data"]
    key = data["key"]

    # Skip own messages
    if key.get("fromMe", False):
        return {"status": "skipped"}

    sender_jid = key["remoteJid"]
    message_text = (
        data["message"].get("conversation")
        or data["message"].get("extendedTextMessage", {}).get("text")
    )

    if not message_text:
        return {"status": "unsupported_type"}

    # Load conversation context from Omega
    context = await omega_query(
        namespace="whatsapp-conversations",
        key=sender_jid,
        limit=10
    )

    # Generate AI response via Claude
    reply = await call_claude(
        system_prompt=WHATSAPP_PERSONA_PROMPT,
        conversation_history=context,
        new_message=message_text
    )

    # Throttle: randomized delay (3-8s)
    await asyncio.sleep(random.uniform(3, 8))

    # Send reply via Evolution API
    await send_evolution_message(
        instance="hermes-wa",
        to=sender_jid,
        text=reply
    )

    # Store turn in Omega
    await omega_store(
        namespace="whatsapp-conversations",
        key=sender_jid,
        value={
            "sender": sender_jid,
            "incoming": message_text,
            "reply": reply,
            "timestamp": datetime.utcnow().isoformat()
        },
        ttl=172800  # 48 hours
    )

    return {"status": "replied"}
```

**Key implementation details:**
- FastAPI handles the webhook endpoint — lightweight, async-native
- Omega Memory stores conversation context per contact JID
- Claude API call includes a system prompt defining the responder persona and boundaries
- Randomized delay before replying mimics human behaviour
- The handler is stateless — all state lives in Omega and Evolution API

_Sources: [FreeCodeCamp Evolution API bot tutorial](https://www.freecodecamp.org/news/how-to-build-and-deploy-a-production-ready-whatsapp-bot/), [Evolution API webhooks docs](https://doc.evolution-api.com/v2/en/configuration/webhooks), [FastAPI webhooks](https://fastapi.tiangolo.com/advanced/openapi-webhooks/)_

#### Phase 3: Wire Into Hermes (Day 3-4)

Two approaches depending on Hermes's current capabilities:

**Approach A: Hermes runs the webhook as a managed skill**
- Deploy the FastAPI webhook as a Docker service in the same compose stack
- Hermes invokes it via MCP or direct HTTP
- Hermes's cron scheduling (Epic 3, story 3-3) could handle health checks

**Approach B: Hermes uses a WhatsApp MCP server**
- Install one of the existing WhatsApp MCP servers (e.g. `whatsapp-mcp-ts`)
- Hermes gains `search_messages`, `send_message`, `list_contacts` tools
- Combine with a cron job that polls for new messages every 30-60 seconds
- Less real-time than webhooks, but simpler MCP-native integration

**Recommendation**: Approach A for real-time auto-reply. Approach B can be added later for Hermes to proactively search conversation history or manage contacts.

#### Phase 4: System Prompt Engineering (Day 4)

The system prompt defines how the AI responds. For a WhatsApp Business auto-responder:

```
You are Tom's assistant responding to WhatsApp Business messages.

Rules:
- Keep replies concise (1-3 sentences max for WhatsApp)
- Match the language of the incoming message
- For questions you can answer: respond directly
- For questions requiring Tom's personal input: acknowledge and say Tom will follow up
- Never share personal information, passwords, or financial details
- Never pretend to be Tom — always frame as "Tom's assistant"
- For urgent matters: flag the message for Tom's immediate attention
```

#### Phase 5: Testing and Hardening (Day 5)

| Test | Method |
|------|--------|
| Basic reply flow | Send test message from another phone → verify reply |
| Conversation context | Send multi-turn conversation → verify context preserved |
| Media handling | Send image/voice → verify graceful handling (or transcription) |
| Rate limiting | Send burst of messages → verify throttling works |
| Session recovery | Restart Evolution API → verify auto-reconnect |
| Failure fallback | Kill Claude API → verify canned fallback response |
| Monitoring | Check Prometheus metrics / Grafana dashboard for message counts |

### Technology Stack Summary

| Component | Technology | Purpose | Resource |
|-----------|-----------|---------|----------|
| WhatsApp bridge | Evolution API v2 | Protocol translation, message relay | ~256MB RAM |
| Database | PostgreSQL 17 | Message history, session persistence | ~128MB RAM |
| Cache | Redis 8 | Session state, rate limiting | ~64MB RAM |
| Webhook handler | FastAPI (Python) | Message processing, AI orchestration | ~64MB RAM |
| AI engine | Claude API (Anthropic) | Response generation | External API |
| Memory | Omega Memory | Conversation context, contact profiles | Existing infra |
| Orchestrator | Hermes Agent | Skill management, scheduling, monitoring | Existing infra |
| **Total new** | | | **~512MB RAM** |

### Cost Analysis

| Item | Cost |
|------|------|
| Evolution API | Free (open source) |
| PostgreSQL + Redis | Free (self-hosted) |
| LXC container | Free (existing Proxmox) |
| Claude API | ~$0.003-0.015 per response (Sonnet/Opus) |
| WhatsApp Business | Free (Business app) or $0.005-0.08/conversation (Cloud API) |
| **Ongoing cost** | **Primarily Claude API usage — estimated $1-5/month for light personal use** |

### Risk Mitigation Strategy

| Risk | Mitigation |
|------|------------|
| WhatsApp bans account | Use Business account (lower risk); reply-only mode; human-like pacing; have a backup number |
| Evolution API breaks after WhatsApp update | Pin to stable version; monitor Evolution API GitHub for breaking changes; have manual fallback |
| Claude API costs spike | Set monthly budget cap; use Haiku for simple replies, Sonnet for complex ones; cache common responses |
| Privacy concerns | All data stays on your homelab; no cloud storage; PostgreSQL encryption at rest; audit logging |
| Message quality issues | Comprehensive system prompt with guardrails; periodic review of AI responses; easy opt-out for contacts |

### Success Metrics

| Metric | Target |
|--------|--------|
| Reply latency (end-to-end) | < 10 seconds |
| Reply accuracy (relevant, helpful) | > 90% |
| WhatsApp account health | Quality rating stays GREEN |
| Uptime | > 99% (Docker restart policy) |
| Cost per month | < $5 for light personal use |

_Sources: [Evolution API docs](https://doc.evolution-api.com/v2/en/install/docker), [WhatsApp messaging limits](https://developers.facebook.com/docs/whatsapp/messaging-limits/), [Claude on WhatsApp via Evolution API MCP](https://skywork.ai/skypage/en/unlocking-claude-whatsapp-evolution-api/1977587287502942208)_

---

## Research Synthesis and Conclusions

### Feasibility Verdict

| Dimension | Assessment | Confidence |
|-----------|-----------|------------|
| **Technical feasibility** | Fully feasible — all components exist, are open-source, Docker-ready | HIGH |
| **Infrastructure fit** | Perfect fit for Proxmox/LXC/Docker homelab stack | HIGH |
| **Hermes integration** | Natural fit via webhook skill or MCP server | HIGH |
| **WhatsApp ToS compliance** | Structured business auto-reply is allowed; general-purpose AI chatbot is banned | HIGH |
| **Ban risk (Evolution API/Baileys)** | Non-zero but manageable with business account + reply-only design | MEDIUM |
| **Production stability (Evolution API)** | Good for personal/low-volume use; not enterprise-grade | MEDIUM |
| **Cost** | Negligible — $1-5/month Claude API for light use | HIGH |

### Recommended Path

**Evolution API + FastAPI webhook → Hermes → Claude API** (Architecture Option A)

This is the most direct, lightest-weight path. It fits the existing homelab stack, reuses Hermes's Omega Memory for conversation context, and can be built in approximately 5 days. The full stack runs in a single LXC container with ~512MB RAM.

### What Makes This Work for a Business Account

1. **WhatsApp Business App** allows linked devices (what Evolution API uses) — this is how WhatsApp Web works natively
2. **Structured auto-reply bots** are explicitly permitted under WhatsApp's Jan 2026 policy update — you're not running a general-purpose chatbot, you're running an assistant that handles specific message types
3. **Reply-only mode** means the bot never initiates contact, staying within WhatsApp's customer service window
4. **Human-like pacing** (3-8s randomized delay) reduces behavioural detection risk

### Open Questions for Implementation

1. **Hermes Epic 3 dependency** — story 3-3 (cron scheduling) and 3-4 (guardrails) would benefit this project. Consider completing Epic 3 first, or implementing the WhatsApp skill in parallel.
2. **Persona design** — how should the assistant present itself? "Tom's assistant" is the safest framing. Should it handle all messages, or only respond to specific contacts/keywords?
3. **Escalation flow** — when the AI can't help, how should it escalate? Flag for Tom in a notification channel? Queue for later?
4. **Media handling** — should the bot handle voice notes (transcribe via Whisper) and images, or only text?
5. **Multi-language** — should it auto-detect and respond in the sender's language?

### Alternative: WhatsApp Cloud API (Official)

If ban risk is unacceptable, the official WhatsApp Cloud API is available for Business accounts. Trade-offs:
- **Pro**: Fully ToS-compliant, no ban risk, Meta-hosted infrastructure
- **Con**: Requires Meta Business verification, per-conversation pricing ($0.005-0.08), less flexibility, general-purpose AI chatbot still banned
- **Verdict**: Worth evaluating if the Baileys approach proves unstable, but Evolution API is the better starting point for a homelab

### Source Inventory

All technical claims in this document are verified against current (2025-2026) sources:

| Category | Key Sources |
|----------|-------------|
| Evolution API | [Official docs](https://doc.evolution-api.com/v2/en/install/docker), [GitHub](https://github.com/EvolutionAPI/evolution-api), [DeepWiki architecture](https://deepwiki.com/EvolutionAPI/evolution-api/6.1-chatbot-architecture-and-sessions) |
| WhatsApp Policy | [TechCrunch](https://techcrunch.com/2025/10/18/whatssapp-changes-its-terms-to-bar-general-purpose-chatbots-from-its-platform/), [respond.io](https://respond.io/blog/whatsapp-general-purpose-chatbots-ban), [MEF](https://mobileecosystemforum.com/2025/12/01/metas-whatsapp-ai-chatbot-ban/) |
| Baileys/Ban Risk | [Baileys wiki](https://baileys.wiki/docs/intro/), [Ban issues](https://github.com/WhiskeySockets/Baileys/issues/1869), [whatsmeow risk](https://github.com/tulir/whatsmeow/issues/810) |
| WhatsApp MCP | [whatsapp-mcp](https://github.com/lharries/whatsapp-mcp), [whatsapp-mcp-ts](https://github.com/jlucaso1/whatsapp-mcp-ts), [Composio](https://composio.dev/toolkits/whatsapp/framework/claude-code) |
| Matrix Bridge | [mautrix-whatsapp](https://docs.mau.fi/bridges/go/setup.html?bridge=whatsapp), [GitHub](https://github.com/mautrix/whatsapp) |
| Rate Limits | [WhatsApp messaging limits](https://developers.facebook.com/docs/whatsapp/messaging-limits/), [Rate limits guide](https://wasenderapi.com/blog/whatsapp-api-rate-limits-explained-how-to-scale-messaging-safely-in-2025) |
| n8n Integration | [n8n WhatsApp AI templates](https://n8n.io/workflows/2845-complete-business-whatsapp-ai-powered-rag-chatbot-using-openai/) |
| Production Stability | [Evolution API problems 2025](https://wasenderapi.com/blog/evolution-api-problems-2025-issues-errors-best-alternative-wasenderapi), [gurusup review](https://gurusup.com/blog/evolution-api-whatsapp) |

---

**Technical Research Completion Date:** 2026-04-14
**Research Methodology:** Web-verified technical research with multi-source validation
**Confidence Level:** HIGH — all core claims verified against current (2025-2026) sources
**Verdict:** Technically feasible. Recommended approach: Evolution API + Hermes webhook skill. ~5 days to implement, ~512MB RAM, ~$1-5/month.
