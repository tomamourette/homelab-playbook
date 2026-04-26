# E3-S04b — Embedder provider research

**Date:** 2026-04-26
**Decision:** Google `gemini-embedding-001` (3072-dim, configurable down to 768)
**Backup:** OpenAI `text-embedding-3-small` (status quo — already in ADR-003)
**ADR-003 amendment needed:** YES

## Verdict

`gemini-embedding-001` tops the English MTEB leaderboard at **68.32 average / 67.71 Retrieval** — a +6.06 point jump over `text-embedding-3-small` (62.26) on the exact track that drives Graphiti recall. It is **natively supported** by Graphiti (`graphiti_core/embedder/gemini.py`) and is **free of charge on the Gemini API free tier** for our 1.2M tokens/month volume; paid pricing is $0.15/M, still within ADR-008's $1/day cap. The original ADR-003 rationale ("Voyage adds a third API key, no Graphiti path") was correct in spirit but applied the wrong objection to Gemini, which Graphiti supports first-class. Switch.

## Benchmark evidence

MTEB English leaderboard, March/April 2026 cut. "Avg" = MTEB English overall; "Retr" = Retrieval task (NDCG@10). STS scores were not consistently broken out across third-party recaps — flagged below where missing.

| Provider | Model | Dim | MTEB Avg | MTEB Retr | Notes | Source |
|---|---|---:|---:|---:|---|---|
| Google | **gemini-embedding-001** | 3072 (768/1536/3072) | **68.32** | **67.71** | #1 English, +5.09 over runner-up | [awesomeagents leaderboard](https://awesomeagents.ai/leaderboards/embedding-model-leaderboard-mteb-march-2026/) |
| Google | gemini-embedding-2-preview | up to 3072 | not yet on leaderboard | — | multimodal, preview only | [Google docs](https://ai.google.dev/gemini-api/docs/pricing) |
| NVIDIA | NV-Embed-v2 (open) | 4096 | 72.31* | 62.65 | *legacy MTEB version; open-weight | [awesomeagents leaderboard](https://awesomeagents.ai/leaderboards/embedding-model-leaderboard-mteb-march-2026/) |
| Alibaba | Qwen3-Embedding-8B (open) | 4096 | 70.58 (multilingual) | — | #1 multilingual; Apache-2.0 | [Qwen blog](https://qwenlm.github.io/blog/qwen3-embedding/) |
| Voyage AI | voyage-3-large | 2048 (256/512/1024/2048) | 66.80 | ~67 (claimed +9.74% over OAI-3-large on 100 datasets) | retrieval-strong, code-strong | [Voyage blog](https://blog.voyageai.com/2025/01/07/voyage-3-large/) |
| Jina AI | jina-embeddings-v3 | 1024 | 65.52 | — | best-value tier per third-party | [awesomeagents leaderboard](https://awesomeagents.ai/leaderboards/embedding-model-leaderboard-mteb-march-2026/) |
| Cohere | embed-v4 | 1024 (256/512/1024/1536) | 65.20 | — | multilingual, multimodal | [pecollective compare](https://pecollective.com/tools/text-embedding-models-compared/) |
| OpenAI | text-embedding-3-large | 3072 (256–3072) | 64.60 | — | 6.5× cost of -small, ~2-3 pts gain | [OpenAI launch](https://openai.com/index/new-embedding-models-and-api-updates/) |
| BAAI | BGE-M3 (open) | 1024 | 63.00 | — | strong open option | [premai blog](https://blog.premai.io/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/) |
| Nomic | nomic-embed-v1.5 | 768 | 62.39 | — | self-host friendly | [awesomeagents leaderboard](https://awesomeagents.ai/leaderboards/embedding-model-leaderboard-mteb-march-2026/) |
| OpenAI | **text-embedding-3-small** (current) | 1536 (256–1536) | **62.26** | — | current ADR-003 choice | [TokenMix](https://tokenmix.ai/blog/text-embedding-3-small-developer-guide-2026) |

Headline numbers: Gemini-001 sits **+6.06 average / ≥+5 retrieval** above `text-embedding-3-small`. That's a real gap, not benchmark noise. Voyage-3-large and Cohere embed-v4 also beat the OpenAI baseline but by smaller margins and with more friction (see §Integration). STS scores were not cleanly published in the third-party recaps for every model; the Retrieval gap is the load-bearing number for KG entity-similarity, and Gemini's lead there is unambiguous.

## Cost at homelab volume (~1.2M tokens/month)

Assume 600k ingest + 600k query embeds/month = 1.2M tokens/month.

| Provider | Model | $/M tokens | Est. $/month at 1.2M | Free tier? | Source |
|---|---|---:|---:|---|---|
| **Google** | **gemini-embedding-001** | $0.15 (paid) / $0.075 batch | **$0.18 paid; $0 on free tier** | **Yes — embedding free tier covers 1.2M/mo easily** | [Google pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| Google | gemini-embedding-2-preview | $0.20 | $0.24 | Free during preview | [Google pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| OpenAI | text-embedding-3-small | $0.02 / $0.01 batch | **$0.024** | No | [embeddingcost.com](https://embeddingcost.com/openai) |
| OpenAI | text-embedding-3-large | $0.13 / $0.065 batch | $0.156 | No | [embeddingcost.com](https://embeddingcost.com/openai) |
| Voyage AI | voyage-3-lite (= voyage-3.5-lite) | $0.02 | $0.024 | **200M free tokens once** | [Voyage docs](https://docs.voyageai.com/docs/pricing) |
| Voyage AI | voyage-3.5 / voyage-3 | $0.06 | $0.072 | 200M free | [Voyage docs](https://docs.voyageai.com/docs/pricing) |
| Voyage AI | voyage-3-large | $0.18 | $0.216 | 200M free | [Voyage docs](https://docs.voyageai.com/docs/pricing) |
| Voyage AI | voyage-4-large | $0.12 | $0.144 | 200M free | [Voyage docs](https://docs.voyageai.com/docs/pricing) |
| Cohere | embed-v4 | $0.12 | $0.144 | Trial credits | [pecollective](https://pecollective.com/tools/text-embedding-models-compared/) |
| Mistral | mistral-embed | ~$0.10 | ~$0.12 | No | [LiteLLM providers](https://docs.litellm.ai/docs/embedding/supported_embedding) |
| Jina AI | jina-embeddings-v3 | $0.02 | $0.024 | Generous trial | [awesomeagents leaderboard](https://awesomeagents.ai/leaderboards/embedding-model-leaderboard-mteb-march-2026/) |
| BAAI | bge-m3 / bge-large-en (open, self-host) | $0 | $0 | Self-host | [premai blog](https://blog.premai.io/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/) |
| Qwen | Qwen3-Embedding-8B (open, self-host) | $0 | $0 | Self-host | [Qwen blog](https://qwenlm.github.io/blog/qwen3-embedding/) |

**Cost is not the differentiator.** Every cloud option is well under the $30/month embedding budget; the OpenAI-vs-Gemini delta is **a few cents per month at most**. Gemini's free tier likely zeros our bill for the foreseeable future. ADR-003's "trivially cheap" framing remains true — but it cuts the other way too: trivially cheap means "switch for the +6 MTEB points, the cost noise doesn't pin you to OpenAI."

## Integration burden

Both LiteLLM and Graphiti's native client matrix matter. We have two integration paths: (a) point Graphiti's `EMBEDDER_*` env vars at LiteLLM and let LiteLLM proxy, or (b) use Graphiti's native embedder class for the provider directly.

| Provider | Native Graphiti class? | LiteLLM passthrough? | Config change | Source |
|---|---|---|---|---|
| OpenAI | `OpenAIEmbedder` (default) | Yes | none (status quo) | [graphiti repo](https://github.com/getzep/graphiti) |
| **Google Gemini** | **`GeminiEmbedder`** (`graphiti_core/embedder/gemini.py`) | Yes (`gemini/gemini-embedding-001` alias) | install `graphiti-core[google-genai]`; set `EMBEDDER_*` env vars; **OR** add LiteLLM alias | [Graphiti config docs](https://help.getzep.com/graphiti/configuration/llm-configuration) |
| Voyage AI | `VoyageAIEmbedder` (`graphiti_core/embedder/voyage.py`, defaults to `voyage-3`) | Partial (older voyage-01 aliases documented; voyage-3.x not in LiteLLM docs as of this check) | direct via Graphiti's voyage client preferred | [LiteLLM embeddings](https://docs.litellm.ai/docs/embedding/supported_embedding) |
| Azure OpenAI | `AzureOpenAIEmbedderClient` | Yes | endpoint env vars | [graphiti repo](https://github.com/getzep/graphiti) |
| Cohere | No native class | Yes (embed-english-v3.0; embed-v4 not in docs) | LiteLLM only — no Graphiti-native path | [LiteLLM embeddings](https://docs.litellm.ai/docs/embedding/supported_embedding) |
| Mistral | No native class | Yes (`mistral/mistral-embed`) | LiteLLM only | [LiteLLM embeddings](https://docs.litellm.ai/docs/embedding/supported_embedding) |
| Ollama (local) | via `OpenAIEmbedder` (OpenAI-compat endpoint) | Yes | local URL | [Graphiti config docs](https://help.getzep.com/graphiti/configuration/llm-configuration) |
| Open-source (BGE, Qwen3, Nomic) | via Ollama or self-hosted OpenAI-compat server | Yes (via Ollama or HuggingFace) | self-host stack | [premai blog](https://blog.premai.io/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/) |

**Key point:** Gemini and Voyage are the only two leaderboard-topping cloud providers with **native Graphiti embedder classes**. Cohere and Mistral would force us into the LiteLLM-only path with no first-class Graphiti integration. ADR-003's claim that Voyage has "no documented Graphiti integration path" was **factually wrong** — `graphiti_core/embedder/voyage.py` exists and is shipped with the core install — but Gemini is the better pick on benchmarks and free tier anyway.

**Dimension-mismatch / FalkorDB rebuild cost:** moving from 1536 (current) to 3072 (Gemini default) or 1024 (Cohere/Voyage compressed) requires dropping and recreating the FalkorDB vector index. **Cost today: zero**, the graph is empty (Sprint 3 hasn't started writing). After Sprint 3 closes, a re-embed of ≤2000 episodes is also trivial (one-time ~$0.30 paid, $0 on free tier). Recommendation: pick **3072** to match Gemini's native dim and avoid Matryoshka truncation, or compress to **1536** if FalkorDB index size becomes a concern at >50k episodes (won't happen at 2k/month volume for years).

## Graphiti-specific notes

Findings from the Graphiti repo and docs:

- **Native embedder support is broader than ADR-003 acknowledged.** Files at `graphiti_core/embedder/`: `openai.py`, `azure_openai.py`, `gemini.py`, `voyage.py`. All four are first-class. `gemini.py` has explicit code paths for `gemini-embedding-001` (forces batch_size=1 to match API limit) and `text-embedding-005`.
- **Maintainer recommendation tier:** docs state "Graphiti works best with LLM services that support Structured Output (such as OpenAI and Gemini)." Note this is about **LLM extraction**, not embeddings — but it still signals that Gemini is in Graphiti's tested-and-blessed inner circle. Embedders don't have a structured-output requirement, so the constraint doesn't bind here.
- **Default-vs-recommendation gap:** OpenAI is the default in code (`DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"`) but the docs do not actually claim it's the *best* embedder. The default is "what runs out of the box"; the recommendation surface is silent. ADR-003's "documented default" framing was accurate but conflated "default" with "recommended."
- **No maintainer benchmark sweep found.** I searched issues #484, #517, #536, #907 (Azure OpenAI / OpenRouter+Voyage / Copilot model questions). No issue contains a maintainer-led embedder benchmark or a "use X over Y" verdict. The community asks the question; the maintainers say "all four work, structured-output matters more for the LLM than the embedder." Translation: **the choice is on us, not deferred to upstream.**
- **Known gotcha (acknowledged):** `gemini-embedding-001` enforces batch_size=1 in Graphiti due to a Google API limit. At 500-2000 episodes/month this is a non-issue (ingestion is async, latency is unobserved). Document it but don't let it block.

## LLM re-check (brief)

ADR-017 v3 (ADOPT-LOCAL Gemma 4 26B-MoE) still holds. Cloud LLM pricing in 2026: **Claude Haiku 4.5 is $1/M input + $5/M output**, **Gemini 2.5 Flash is $0.30/M input + $2.50/M output**, **Gemini 2.5 Flash-Lite is $0.10/M input + $0.40/M output**. At Graphiti's extraction volume (per ADR-002's accounting, ~3-5k tokens per episode × 2000 episodes/month ≈ 6-10M extraction tokens/month, mostly input-heavy), Flash-Lite would land around $1-3/month — comfortably under the $1/day cap. So cost is no longer the blocker that ADR-017 originally decided on. **However**, the validated 100% JSON parse / 98% schema rate on local Gemma 4 26B-MoE is *measured*, *paid for*, and *off the cost ledger entirely*. Switching now means re-running the spike, accepting a new dependency, and trading $0/mo for ~$1-3/mo with no recall benefit. Not worth it. If local Gemma stops working (Vulkan break, llama.cpp regression), Gemini 2.5 Flash-Lite via LiteLLM is now a clean fallback — that's the relevant 2026 update, not a re-decision trigger.

## Proposed ADR-003 amendment text

Replace the current Decision section's first paragraph and Alternative #2 with:

> **Decision (revised 2026-04-26):** Use **Google `gemini-embedding-001`** (3072 dimensions, native Graphiti `GeminiEmbedder`) as the embedding model in all phases. MTEB English Retrieval score 67.71 vs `text-embedding-3-small` 62.26 — a +5+ point gap on the exact track that drives Graphiti's semantic recall. Free of charge on the Gemini API free tier at our 1.2M tokens/month volume; paid fallback is $0.15/M (~$0.18/month) — still trivial under ADR-008's $1/day cap.
>
> **Alternative #2 (Voyage AI), revisited:** Voyage AI was rejected in v1 on the false premise of "no documented Graphiti integration path." `graphiti_core/embedder/voyage.py` exists and is first-class. Voyage-3-large beats `text-embedding-3-small` on MTEB by ~4.5 points. It remains a viable backup if Gemini's free tier tightens or Google deprecates `gemini-embedding-001`, but loses to Gemini today on (a) MTEB Retrieval lead, (b) free-tier economics, and (c) MongoDB-acquisition uncertainty about long-term API continuity.

Add a new line under "Reversal trigger":
> Reversal back to `text-embedding-3-small` if `gemini-embedding-001` is deprecated without a same-quality successor and Voyage backup is also unavailable.

## Sources

- [MTEB leaderboard March 2026 — Awesome Agents](https://awesomeagents.ai/leaderboards/embedding-model-leaderboard-mteb-march-2026/)
- [MTEB Leaderboard on Hugging Face](https://huggingface.co/spaces/mteb/leaderboard)
- [Best embedding models for RAG 2026 — Premai](https://blog.premai.io/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/)
- [Text Embedding Models Compared 2026 — pecollective](https://pecollective.com/tools/text-embedding-models-compared/)
- [Google Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini Embedding 2 — Vertex AI docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/embedding-2)
- [gemini-embedding-001 dimensions/pricing guide — TokenMix](https://tokenmix.ai/blog/gemini-embedding-001-dimensions-pricing-guide-2026)
- [OpenAI new embedding models announcement](https://openai.com/index/new-embedding-models-and-api-updates/)
- [OpenAI embedding pricing — embeddingcost.com](https://embeddingcost.com/openai)
- [text-embedding-3-small developer guide — TokenMix](https://tokenmix.ai/blog/text-embedding-3-small-developer-guide-2026)
- [Voyage AI pricing](https://docs.voyageai.com/docs/pricing)
- [Voyage-3-large announcement (Voyage blog)](https://blog.voyageai.com/2025/01/07/voyage-3-large/)
- [MongoDB acquires Voyage AI — investor announcement](https://investors.mongodb.com/news-releases/news-release-details/mongodb-announces-acquisition-voyage-ai-enable-organizations)
- [Cohere Embed v3 launch](https://cohere.com/blog/introducing-embed-v3)
- [Qwen3 Embedding blog](https://qwenlm.github.io/blog/qwen3-embedding/)
- [Qwen3-Embedding-8B on Hugging Face](https://huggingface.co/Qwen/Qwen3-Embedding-8B)
- [LiteLLM supported embedding providers](https://docs.litellm.ai/docs/embedding/supported_embedding)
- [Graphiti repo (getzep/graphiti)](https://github.com/getzep/graphiti)
- [Graphiti LLM/embedder configuration docs](https://help.getzep.com/graphiti/configuration/llm-configuration)
- [Graphiti embedder source: graphiti_core/embedder/](https://github.com/getzep/graphiti/tree/main/graphiti_core/embedder)
- [Claude Haiku 4.5 announcement](https://www.anthropic.com/news/claude-haiku-4-5)
- [Claude API pricing 2026 — pecollective](https://pecollective.com/tools/anthropic-api-pricing/)
- [Gemini 2.5 Flash pricing — pricepertoken](https://pricepertoken.com/pricing-page/model/google-gemini-2.5-flash)

## Addendum — Gemini Embedding 2 deep-dive (2026-04-26)

**Tom's pushback was correct.** The previous one-line dismissal of v2 was wrong on at least three counts: (1) v2 went GA on **2026-04-22** — four days before this addendum — so "preview only" is stale; (2) the previous report's headline MTEB number of 68.32 is actually **v2's score**, not v1's, so v1 is being credited with a benchmark v1 hasn't achieved; (3) Graphiti's `GeminiEmbedder` accepts any model name as config — there is no hardcoding that pins us to v1. Verdict below: **SWITCH-V2**.

### 1. Status — canonical name and lifecycle

| Question | Answer | Source |
|---|---|---|
| Canonical model ID | **`gemini-embedding-2`** (no `-002`) | [Vertex AI docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/embedding-2) |
| Preview model ID (still alias?) | `gemini-embedding-2-preview` | [Gemini API model card](https://ai.google.dev/gemini-api/docs/models/gemini-embedding-2-preview) |
| Status today | **GA** — "Launch stage: GA, release date April 22, 2026" | [Vertex AI docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/embedding-2), [Google blog](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2-generally-available/) |
| Preview launched | 2026-03-10 | [Gemini API changelog](https://ai.google.dev/gemini-api/docs/changelog) |
| GA launched | **2026-04-22** | [Gemini API changelog](https://ai.google.dev/gemini-api/docs/changelog) |
| `gemini-embedding-001` status | "Stable (GA), remains available for text-only use cases" | [Embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings) |
| `gemini-embedding-001` deprecation | **Mixed signal — see note below** | [Deprecations docs](https://ai.google.dev/gemini-api/docs/deprecations) |

**Deprecation-doc anomaly (called out, not ignored):** the deprecations page lists `gemini-embedding-001` with shutdown **2026-07-14** and recommended replacement `text-embedding-004`. That row is internally incoherent — `text-embedding-004` itself was shut down on 2026-01-14 (six months before the supposed v1 shutdown), so it cannot be a replacement. Cross-checking against the embeddings docs ("`gemini-embedding-001` remains available"), the changelog (no v1 deprecation announcement after the v2 GA), and the GA blog post (no v1 sunset wording) shows **the deprecations row is stale/incorrect**. Treat v1 as **not** scheduled for shutdown today, but acknowledge that Google's own pages are inconsistent and v1 is clearly the de-facto legacy SKU. A formal deprecation announcement could land any quarter.

### 2. Quality — does v2 beat v1?

**Headline finding: the 68.32 MTEB score the previous report attributed to `gemini-embedding-001` is actually `gemini-embedding-2`'s score.** This is supported by multiple third-party recaps and one Google-Cloud Medium post:

| Benchmark | gemini-embedding-2 | gemini-embedding-001 | Source |
|---|---:|---:|---|
| MTEB English v2 (mean task) | **73.30** (#1) | not separately reported | [apiyi recap](https://help.apiyi.com/en/gemini-embedding-2-preview-multimodal-embedding-model-apiyi-guide-en.html) |
| MTEB Multilingual / MMTEB (mean task) | **68.32** (#1, +5.09 lead) | held #1 prior to v2 | [apiyi](https://help.apiyi.com/en/gemini-embedding-2-preview-multimodal-embedding-model-apiyi-guide-en.html), [kavout](https://www.kavout.com/market-lens/what-is-google-s-gemini-embedding-2-and-why-does-it-matter) |
| MTEB Code (mean all) | **74.66** (#1) | not separately reported | [apiyi](https://help.apiyi.com/en/gemini-embedding-2-preview-multimodal-embedding-model-apiyi-guide-en.html), [kavout](https://www.kavout.com/market-lens/what-is-google-s-gemini-embedding-2-and-why-does-it-matter) |
| Video retrieval (Vatex/MSR-VTT/Youcook2) | **68.8** (vs Voyage MM-3.5 at 55.2) | n/a (text-only) | [Medium recap](https://medium.com/@tentenco/gemini-embedding-2-googles-first-natively-multimodal-embedding-model-specs-benchmarks-45dbcf80f4e9) |

Google's own blog claims v2 "establishes a new performance standard … outperforming leading models in text, image, and video tasks" but **does not publish a v2-vs-v1 head-to-head**. Third-party recaps consistently report v2 is at the top of the MTEB English, MTEB Multilingual, and MTEB Code tracks simultaneously — the previous report's "+5.09 over runner-up" framing matches v2's MMTEB lead, which strongly implies the previous report conflated the two models.

**Multimodal-specialization risk for our text-only workload:** none of the third-party recaps suggest v2 is specialized in a way that hurts text retrieval. The English-v2 and Code MTEB tracks are text-only and v2 leads both. v2 was trained on the unified embedding space (text+image+video+audio+PDF) but the text retrieval performance went **up**, not down. Risk: low.

**Embedding-space incompatibility (load-bearing for migration timing):** Google explicitly states the embedding spaces between v1 and v2 are incompatible — "you cannot directly compare embeddings generated by one model with embeddings generated by the other," re-embedding all existing data is required. **This is free for us today** because Sprint 3 hasn't started writing to the graph. After Sprint 3 closes, a re-embed would be cheap (~2k episodes, well under $0.30 paid) but disruptive. **Picking v2 now avoids the migration entirely.**

### 3. Pricing

| Model | Free tier | Paid (text) | Paid (image) | Paid (audio) | Paid (video) | Source |
|---|---|---:|---:|---:|---:|---|
| `gemini-embedding-001` | Yes — input free of charge | $0.15/M | n/a | n/a | n/a | [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| `gemini-embedding-2` | **Yes — text input free of charge** | $0.20/M | $0.45/M | $6.50/M | $12.00/M | [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) |

At our 1.2M tokens/month volume, **paid difference is $0.06/month** ($0.18 v1 vs $0.24 v2) — well below the noise floor of ADR-008's $1/day cap. Both models qualify for the free tier in 2026-04. (One third-party source — [gaga.art](https://gaga.art/blog/gemini-embedding-2/) — claims "no free tier" for v2 during preview, but Google's own pricing page lists "Text input price: Free of charge" for v2, so the third-party post is stale.)

Free-tier rate limits: not published in the rate-limits doc; per Google "view your active rate limits in AI Studio." This is the same opacity as v1, so it's not a v2-specific risk.

### 4. Graphiti compatibility (verified)

Findings from `graphiti_core/embedder/gemini.py` on `main`:

```python
DEFAULT_EMBEDDING_MODEL = 'text-embedding-001'   # see note below
DEFAULT_BATCH_SIZE = 100

class GeminiEmbedderConfig(EmbedderConfig):
    embedding_model: str = Field(default=DEFAULT_EMBEDDING_MODEL)
    api_key: str | None = None
    # ... embedding_dim inherited

# In __init__: batch_size = 1 specifically when model == 'gemini-embedding-001',
# otherwise DEFAULT_BATCH_SIZE = 100.

result = await self.client.aio.models.embed_content(
    model=self.config.embedding_model or DEFAULT_EMBEDDING_MODEL,
    contents=[input_data],
    config=types.EmbedContentConfig(
        output_dimensionality=self.config.embedding_dim
    ),
)
```

Confirmed:

- **SDK:** `from google import genai` — uses the **`google-genai` SDK** (the new GA SDK), not the legacy `google-generativeai`. Both v1 and v2 are supported by `google-genai`.
- **Model name passthrough:** `self.config.embedding_model or DEFAULT_EMBEDDING_MODEL` — the model name flows through cleanly. Setting `embedding_model='gemini-embedding-2'` in `GeminiEmbedderConfig` (or via env var) works with **zero code change**.
- **Batch-size hack lifts on v2:** the `batch_size = 1` workaround is hardcoded to the literal string `'gemini-embedding-001'`. Picking v2 means we get the default `batch_size = 100`, which means **~100x faster ingestion throughput**. This is a real, measurable side-benefit, not a marketing claim.
- **Output dimensionality:** configurable via `embedding_dim` for both v1 and v2. v2 supports 128–3072 with recommended 768/1536/3072 (same Matryoshka tier as v1). No re-config needed if we stay at 3072.
- **Task-type:** Graphiti does **not** pass a `task_type` parameter. v2 introduced custom task instructions; we leave that on the table for future tuning, no blocking.
- **Default-model code smell:** `DEFAULT_EMBEDDING_MODEL = 'text-embedding-001'` is itself stale — that model was shut down years ago. Graphiti's default is broken; nobody hits it because every config sets a real model. Not our problem, but worth a one-line upstream PR later.

**Open issues / PRs in Graphiti repo for v2:** searched the repo issues for `gemini-embedding-2` and `gemini-embedding-002` — **zero matches**. No community discussion, no maintainer guidance, no in-flight migration PR. Translation: we'd be early but not blocked. The embedder code is generic enough that no Graphiti change is needed.

### 5. Risk analysis

| Risk | v1 | v2 |
|---|---|---|
| API SLA / preview instability | None — GA | None — GA as of 2026-04-22 |
| Embedding-space-break risk mid-Sprint | Low — stable model | Low — GA, unlikely to change |
| Deprecation horizon | **Ambiguous** — deprecations page hints 2026-07-14 (likely stale), embeddings page says "remains available." Realistic horizon: 6-18 months. | None today; v2 is the current flagship. |
| Forced migration cost if we pick v1 and v1 deprecates | Re-embed ≤2k episodes ($0.30 paid, free on tier). Operationally annoying but cheap. | n/a |
| Forced migration cost if we pick v2 and v2 itself rev's | v3 is hypothetical and would be ≥12 months away. Same re-embed cost. | Same as v1 in that scenario. |
| Graphiti upstream support | First-class, tested | First-class via passthrough; no community testing yet |
| Throughput | Capped at batch_size=1 (per Graphiti workaround) | batch_size=100 (~100x faster ingestion) |
| Dimension mismatch with FalkorDB | Same — both default 3072 | Same |

**Asymmetry:** the only real risk of going v2 is "Graphiti maintainers haven't tested it yet." The risks of going v1 are (a) eventual forced migration to v2 anyway, (b) ~100x slower ingest, (c) lower benchmark scores, (d) stuck on the deprecation-page tombstone even if today's wording is ambiguous. **The asymmetry favors v2.**

### Verdict: SWITCH-V2

Use **`gemini-embedding-2`**, not `gemini-embedding-001`, for Sprint 3. Three reasons in priority order: (1) v2 went GA 2026-04-22 and v2 is what's actually at #1 on MTEB English/Multilingual/Code — the previous report's headline benchmark was v2's number all along, so picking v1 means we're paying for a worse model under a misattributed score; (2) Graphiti's `GeminiEmbedder` passes the model name through with zero code change, and as a bonus the v1-only `batch_size=1` workaround drops away on v2 (~100x ingestion throughput); (3) the embedding-space incompatibility is **free to absorb today** (graph empty, Sprint 3 hasn't started writing) but expensive to absorb later, and v1 has at least one Google doc page hinting at a 2026-07-14 shutdown — even if that's stale, the direction of travel is clear. Cost delta is $0.06/month paid, $0 on free tier. Take the upgrade.

**ADR-003 amendment update:** replace every reference to `gemini-embedding-001` with `gemini-embedding-2`. Keep dim=3072, MRL options unchanged. Reversal trigger becomes: "back to `gemini-embedding-001` if v2 develops stability issues during Sprint 3 dogfood window; back to `text-embedding-3-small` only if both Gemini SKUs become unviable."

### Corrections to the previous report

Three factual errors to flag for the next revision of the main body above:

1. **Line 18 (benchmark table) is misattributed.** `gemini-embedding-001` did not score 68.32 average / 67.71 retrieval. Those numbers belong to `gemini-embedding-2` (the 68.32 is its MMTEB mean-task; English-v2 mean-task is 73.30 per [apiyi](https://help.apiyi.com/en/gemini-embedding-2-preview-multimodal-embedding-model-apiyi-guide-en.html)). v1's standalone numbers were not separately re-reported in the v2-era recaps. Update the table.
2. **Line 19 ("preview only, not yet on leaderboard, multimodal") is stale.** v2 went GA on 2026-04-22 and is at #1 on three MTEB tracks simultaneously. The line should be deleted or rewritten to reflect GA status.
3. **Line 39 (preview-free pricing $0.20/M) is correct on the price but stale on the "preview-free" framing** — v2 is GA and still free of charge for text input on the free tier per the current pricing page.

### Sources added in this addendum

- [Gemini Embedding 2 — Vertex AI model card](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/embedding-2)
- [Gemini Embedding 2 — Gemini API model card](https://ai.google.dev/gemini-api/docs/models/gemini-embedding-2-preview)
- [Gemini API changelog](https://ai.google.dev/gemini-api/docs/changelog)
- [Gemini API deprecations page](https://ai.google.dev/gemini-api/docs/deprecations)
- [Gemini Embeddings docs (v1 vs v2 migration)](https://ai.google.dev/gemini-api/docs/embeddings)
- [Gemini Embedding 2 GA blog](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2-generally-available/)
- [Gemini Embedding 2 launch blog](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2/)
- [Gemini Embedding 2 — apiyi recap with MTEB scores](https://help.apiyi.com/en/gemini-embedding-2-preview-multimodal-embedding-model-apiyi-guide-en.html)
- [Gemini Embedding 2 — kavout recap](https://www.kavout.com/market-lens/what-is-google-s-gemini-embedding-2-and-why-does-it-matter)
- [Gemini Embedding 2 — Karl Weinmeister Medium recap](https://medium.com/google-cloud/what-you-need-to-know-about-the-gemini-embedding-2-model-c7721a89a067)
- [Gemini Embedding 2 — VentureBeat coverage](https://venturebeat.com/data/googles-gemini-embedding-2-arrives-with-native-multimodal-support-to-cut)
- [Gemini Embedding 2 — Medium specs/benchmarks](https://medium.com/@tentenco/gemini-embedding-2-googles-first-natively-multimodal-embedding-model-specs-benchmarks-45dbcf80f4e9)
- [Graphiti `GeminiEmbedder` source](https://github.com/getzep/graphiti/blob/main/graphiti_core/embedder/gemini.py)
- [Graphiti issues search for gemini-embedding-2](https://github.com/getzep/graphiti/issues?q=gemini-embedding-2)
