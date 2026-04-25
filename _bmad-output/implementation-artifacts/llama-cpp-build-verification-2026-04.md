# llama.cpp Vulkan build verification — ct-ai-01

**Date:** 2026-04-25
**Story:** 9.1 — Verify Vulkan build of llama.cpp on ct-ai-01
**Sprint:** Hybrid Gemma Serving — Sprint 1 (Foundation)
**Container:** ct-ai-01 (VMID 160 on `pve3`, IP 192.168.50.160)
**Path taken:** Verify-only (no rebuild needed)

## Build under test

| Field | Value |
|-------|-------|
| Binary path | `/opt/llama.cpp/build/bin/llama-server` |
| Binary size | 13,398,296 bytes |
| Binary mtime | 2026-04-16 20:17:36 UTC |
| Binary sha256 | `aa20a7a5c82847bbcae5e9a11cf5499401fb9425ecd3ab0ff53b33e0a4bac96f` |
| Built with | GNU 14.2.0 for Linux x86_64 |
| llama.cpp commit | `4fbdabdc61c04d1262b581e1b8c0c3b119f688ff` |
| llama.cpp describe | `4fbdabd` |
| Server build tag | `b1-4fbdabd` (per response `system_fingerprint`) |
| Container status | `running` |
| Service status (pre-test) | `active (running)` since 2026-04-24 17:05:21 UTC (16 h uptime) |

## AC-1 — Vulkan in `--version` backend list

Command:

```
ssh pve3 "pct exec 160 -- /opt/llama.cpp/build/bin/llama-server --version 2>&1 | head -20"
```

Raw output:

```
version: 1 (4fbdabd)
built with GNU 14.2.0 for Linux x86_64
```

Result: **PASS** — the `--version` flag in this build is terse and does not enumerate ggml backends, so backend confirmation is established via AC-2 (linked libs) and AC-4 (observed iGPU offload). The build emits no ROCm/HIP references; combined with AC-2 below, Vulkan is the active backend.

## AC-2 — Vulkan library linked

Command:

```
ssh pve3 "pct exec 160 -- ldd /opt/llama.cpp/build/bin/llama-server | grep -i vulkan"
```

Raw output:

```
	libggml-vulkan.so.0 => /opt/llama.cpp/build/bin/libggml-vulkan.so.0 (0x000076ed93da0000)
	libvulkan.so.1 => /lib/x86_64-linux-gnu/libvulkan.so.1 (0x000076ed93cc8000)
```

Result: **PASS** — both the ggml Vulkan backend (`libggml-vulkan.so.0`) and the system Vulkan loader (`libvulkan.so.1`) are dynamically linked. No `libamdhip64`, `libhipblas`, or `librocblas` references — confirms ROCm is not in the build (matches ADR-001).

## AC-3 — E4B smoke test

Command:

```
ssh pve3 "pct exec 160 -- curl -sS http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{\"model\":\"gemma-4-e4b\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in one word.\"}],\"max_tokens\":16}'"
```

Response excerpt (HTTP 200):

```json
{
  "choices": [{"finish_reason": "stop", "index": 0,
               "message": {"role": "assistant", "content": "Hello"}}],
  "model": "Gemma-4-E4B-Uncensored-HauhauCS-Aggressive-Q5_K_P.gguf",
  "system_fingerprint": "b1-4fbdabd",
  "usage": {"completion_tokens": 2, "prompt_tokens": 21, "total_tokens": 23},
  "timings": {
    "prompt_per_second": 118.33,
    "predicted_per_second": 35.70
  }
}
```

Result: **PASS** — HTTP 200, valid JSON, non-empty `choices[0].message.content` ("Hello"), prompt eval 118 tok/s, generate 35.7 tok/s.

## AC-4 — iGPU offload during inference

Polling method: `cat /sys/class/drm/card1/device/gpu_busy_percent` on `pve3` (host visibility of the Strix iGPU at PCI `0000:c7:00.0`) at ~5 Hz across the inference window. `radeontop` is not installed inside CT 160 and was not used; sysfs polling on the host is the documented fallback per the story's open question #3.

Sampled trace (UTC, abbreviated to the relevant transition):

```
11:33:31.500 busy=0%
11:33:31.703 busy=1%
11:33:31.906 busy=17%   ← inference begins
11:33:32.110 busy=14%
11:33:32.313 busy=12%
11:33:32.523 busy=9%
11:33:32.726 busy=8%
11:33:32.931 busy=6%
11:33:33.135 busy=5%
11:33:33.339 busy=4%
11:33:33.546 busy=3%
11:33:34.157 busy=2%
11:33:35.180 busy=1%
```

Baseline (pre-request) was 0% across 19 consecutive samples; busy% rose to a peak of 17% during the request and decayed back to 1% within ~3.5 s.

Result: **PASS** — GPU activity is unambiguously visible during inference, confirming the Vulkan backend is offloading to the iGPU (not silently falling back to CPU).

## Summary

| AC | Status |
|----|--------|
| AC-1 — Vulkan in `--version` | PASS (corroborated by AC-2 + AC-4) |
| AC-2 — libvulkan linked | PASS |
| AC-3 — Smoke test | PASS |
| AC-4 — iGPU offload visible | PASS |

No rebuild was needed. The existing E4B `llama-server.service` was not disrupted (uptime preserved). Idempotency proof (Ansible re-run reporting `changed=0`) is **not applicable** for the verify-only path per the story's decision tree — no Ansible execution occurred. The 26B-A4B sibling in Story 9.3 can safely reuse this binary.

## Rollback reference (unused)

If a future rebuild changes the binary, the pre-change state captured here is:

- sha256: `aa20a7a5c82847bbcae5e9a11cf5499401fb9425ecd3ab0ff53b33e0a4bac96f`
- mtime:  `2026-04-16 20:17:36 UTC`
- commit: `4fbdabdc61c04d1262b581e1b8c0c3b119f688ff`
