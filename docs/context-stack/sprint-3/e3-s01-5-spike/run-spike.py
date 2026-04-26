#!/usr/bin/env python3
"""
E3-S01.5 spike runner — validate Gemma 4 26B-MoE for Graphiti extraction.

Reads 50 episodes from corpus-50-facts.jsonl, sends each to LiteLLM gateway
with the extraction prompt, attempts json.loads on the model's response,
records pass/fail + schema conformance + latency, writes results.jsonl.

Configuration (env vars override defaults):
  LITELLM_BASE_URL   default http://192.168.50.160:4000  (LiteLLM gateway on ct-ai-01)
  LITELLM_API_KEY    if unset, read from LITELLM_KEY_FILE (default ~/.litellm-spike-key, mode 600)
  LITELLM_KEY_FILE   path to a mode-600 file holding the bearer token
  MODEL_NAME         default gemma4-26b-text  (per ADR-002 — explicitly the 26B MoE)
  REQUEST_TIMEOUT    seconds; default 180 (Gemma 26B MoE on ct-ai-01 CPU/Vulkan
                     inference is slower than initially assumed — empirically
                     ~30-120s per extraction with max_tokens=2048; the 30s ceiling
                     in the original brief was incorrect, see ADR-017 latency analysis)

The script NEVER hard-codes a key and NEVER prints it.

Usage (the operator-facing way):
  python3 run-spike.py
  # or override defaults:
  LITELLM_BASE_URL=http://10.0.0.1:4000 MODEL_NAME=gemma4-auto python3 run-spike.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
CORPUS_PATH = HERE / "corpus-50-facts.jsonl"
PROMPT_PATH = HERE / "extraction-prompt.txt"
RESULTS_PATH = HERE / "results.jsonl"

REQUIRED_TOP_LEVEL_KEYS = {"entities", "edges", "valid_at", "invalid_at"}
REQUIRED_ENTITY_KEYS = {"name", "summary", "labels"}
REQUIRED_EDGE_KEYS = {"source", "target", "fact", "type"}


def load_prompt() -> tuple[str, str]:
    """Split extraction-prompt.txt into (system, user_template)."""
    raw = PROMPT_PATH.read_text(encoding="utf-8")
    # The prompt file uses ### SYSTEM and ### USER (template) headers.
    parts = raw.split("### USER (template)")
    system = parts[0].replace("### SYSTEM", "").strip()
    user_tmpl = parts[1].strip() if len(parts) > 1 else ""
    return system, user_tmpl


def call_gateway(base_url: str, api_key: str, model: str,
                 system: str, user_msg: str, timeout: int = 180) -> tuple[str, float, dict]:
    """POST to /v1/chat/completions; return (raw_content, latency_s, full_response)."""
    url = base_url.rstrip("/") + "/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        # 1500 (E3-S01.5c 2026-04-26): bumped from 1024 because the director's
        # pre-test on the first v2-failed episode emitted 668 tokens of clean
        # JSON; longer episodes (architectural-decision, supersession-trail)
        # may need more headroom. 1500 keeps a safety margin without becoming
        # wasteful — early-finish completions still report completion_tokens
        # well below the cap.
        "max_tokens": 1500,
        "temperature": 0,
        # Disable Gemma 3's "thinking" mode (E3-S01.5b 2026-04-26). Without
        # this, ~all completions burn the entire max_tokens budget on hidden
        # reasoning tokens and emit empty content with finish_reason=length.
        # Forwarded by gemma-hybrid-proxy verbatim to llama-server, which
        # honours OpenAI's chat_template_kwargs extension.
        "chat_template_kwargs": {"enable_thinking": False},
        # Force JSON-mode at llama-server (E3-S01.5c 2026-04-26). v2 saw 8/11
        # failures from "missing comma in long output" — a known weak point
        # of free-form structured output. response_format=json_object engages
        # llama.cpp's JSON-grammar constrained decoding, eliminating the
        # syntax-error class entirely. Director's probe on the first v2-failed
        # episode confirmed: HTTP 200, 32 s, clean parseable JSON with all 4
        # expected keys. Proxy already accepts the field (openai_models.py L206).
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    elapsed = time.monotonic() - t0
    parsed = json.loads(body)
    content = parsed["choices"][0]["message"].get("content", "") or ""
    return content, elapsed, parsed


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_block(text: str) -> tuple[str, list[str]]:
    """Best-effort isolate the JSON object from the model's raw output.

    Returns (cleaned_text, transformations_applied). Transformations are
    recorded so we can later count how often each repair was needed —
    useful evidence when the spike's verdict depends on whether the
    *model* was clean or whether *post-processing* was load-bearing.

    Steps applied in order:
      1. Strip whitespace.
      2. If the output begins with a markdown code fence (```json or ```),
         remove the opening and closing fence.
      3. If, after fence-strip, the text still has prose around the JSON
         (e.g. "Here is the result: {...}"), grab the first balanced-looking
         JSON object via greedy regex.
    """
    transforms: list[str] = []
    cleaned = text.strip()
    if not cleaned:
        return "", ["empty_response"]

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_]*\n?", "", cleaned, count=1)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()
        transforms.append("stripped_markdown_fences")

    # If the model wrapped JSON in prose, regex-grab the first { ... } block.
    if not (cleaned.startswith("{") and cleaned.endswith("}")):
        m = _JSON_BLOCK_RE.search(cleaned)
        if m:
            cleaned = m.group(0)
            transforms.append("regex_grabbed_json_block")
        # else: leave as-is so json.loads fails with a clear error
    return cleaned, transforms


def strip_fences(text: str) -> str:
    """Backward-compatible shim — returns just the cleaned text."""
    cleaned, _ = extract_json_block(text)
    return cleaned


def evaluate_schema(obj) -> dict:
    """Return a dict of schema-conformance booleans + a short failure-reason summary."""
    result = {
        "is_object": isinstance(obj, dict),
        "has_all_top_keys": False,
        "entities_well_formed": False,
        "edges_well_formed": False,
        "valid_at_ok": False,
        "invalid_at_ok": False,
        "schema_pass": False,
        "schema_fail_reasons": [],
    }
    if not result["is_object"]:
        result["schema_fail_reasons"].append("top_level_not_object")
        return result

    keys = set(obj.keys())
    missing = REQUIRED_TOP_LEVEL_KEYS - keys
    extra = keys - REQUIRED_TOP_LEVEL_KEYS
    if missing:
        result["schema_fail_reasons"].append(f"missing_top_keys:{sorted(missing)}")
    if extra:
        result["schema_fail_reasons"].append(f"extra_top_keys:{sorted(extra)}")
    result["has_all_top_keys"] = not missing  # extras don't fail (lenient)

    # entities
    entities = obj.get("entities")
    if isinstance(entities, list):
        ok = True
        for i, ent in enumerate(entities):
            if not isinstance(ent, dict):
                ok = False
                result["schema_fail_reasons"].append(f"entity[{i}]_not_object")
                break
            ent_missing = REQUIRED_ENTITY_KEYS - set(ent.keys())
            if ent_missing:
                ok = False
                result["schema_fail_reasons"].append(f"entity[{i}]_missing:{sorted(ent_missing)}")
                break
            if not isinstance(ent.get("labels"), list):
                ok = False
                result["schema_fail_reasons"].append(f"entity[{i}].labels_not_array")
                break
        result["entities_well_formed"] = ok
    else:
        result["schema_fail_reasons"].append("entities_not_array")

    # edges
    edges = obj.get("edges")
    if isinstance(edges, list):
        ok = True
        for i, ed in enumerate(edges):
            if not isinstance(ed, dict):
                ok = False
                result["schema_fail_reasons"].append(f"edge[{i}]_not_object")
                break
            ed_missing = REQUIRED_EDGE_KEYS - set(ed.keys())
            if ed_missing:
                ok = False
                result["schema_fail_reasons"].append(f"edge[{i}]_missing:{sorted(ed_missing)}")
                break
        result["edges_well_formed"] = ok
    else:
        result["schema_fail_reasons"].append("edges_not_array")

    # valid_at / invalid_at: must be string or null
    va = obj.get("valid_at", "missing")
    ia = obj.get("invalid_at", "missing")
    result["valid_at_ok"] = (va is None) or isinstance(va, str)
    result["invalid_at_ok"] = (ia is None) or isinstance(ia, str)
    if not result["valid_at_ok"]:
        result["schema_fail_reasons"].append(f"valid_at_wrong_type:{type(va).__name__}")
    if not result["invalid_at_ok"]:
        result["schema_fail_reasons"].append(f"invalid_at_wrong_type:{type(ia).__name__}")

    result["schema_pass"] = (
        result["has_all_top_keys"]
        and result["entities_well_formed"]
        and result["edges_well_formed"]
        and result["valid_at_ok"]
        and result["invalid_at_ok"]
    )
    return result


DEFAULT_BASE_URL = "http://192.168.50.160:4000"
DEFAULT_KEY_FILE = str(Path.home() / ".litellm-spike-key")


def load_api_key() -> tuple[str, str]:
    """Resolve the bearer token without ever printing it.

    Order:
      1. LITELLM_API_KEY env var (highest priority).
      2. LITELLM_KEY_FILE env var pointing at a file (mode 600 expected).
      3. ~/.litellm-spike-key (default file).

    Returns (api_key, source_description). The source_description is safe
    to log (e.g. "env LITELLM_API_KEY" or "file /home/.../.litellm-spike-key");
    the api_key itself MUST NOT be logged.
    """
    env_key = os.environ.get("LITELLM_API_KEY")
    if env_key:
        return env_key.strip(), "env LITELLM_API_KEY"

    key_path = os.environ.get("LITELLM_KEY_FILE", DEFAULT_KEY_FILE)
    p = Path(key_path)
    if not p.is_file():
        raise FileNotFoundError(
            f"No LITELLM_API_KEY in env and key file not found: {key_path}"
        )
    raw = p.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(f"Key file is empty: {key_path}")
    return raw, f"file {key_path}"


def main() -> int:
    base = os.environ.get("LITELLM_BASE_URL", DEFAULT_BASE_URL)
    model = os.environ.get("MODEL_NAME", "gemma4-26b-text")
    timeout = int(os.environ.get("REQUEST_TIMEOUT", "180"))

    try:
        key, key_source = load_api_key()
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    # NEVER print `key` itself; only print where it came from.
    print(f"API key sourced from: {key_source}")

    system, user_tmpl = load_prompt()
    if "{EPISODE_TEXT}" not in user_tmpl:
        print("ERROR: extraction-prompt.txt missing {EPISODE_TEXT} placeholder", file=sys.stderr)
        return 2

    episodes = []
    with CORPUS_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            episodes.append(json.loads(line))

    print(f"Loaded {len(episodes)} episodes from {CORPUS_PATH.name}")
    print(f"Calling {base} model={model} ...")
    print()

    results = []
    t_total = time.monotonic()
    for i, ep in enumerate(episodes, start=1):
        eid = ep["episode_id"]
        cat = ep["category"]
        text = ep["text"]
        user_msg = user_tmpl.replace("{EPISODE_TEXT}", text)

        try:
            raw_content, latency, full_resp = call_gateway(
                base, key, model, system, user_msg, timeout=timeout
            )
            cleaned, transforms = extract_json_block(raw_content)
            had_fences = "stripped_markdown_fences" in transforms
            had_prose = "regex_grabbed_json_block" in transforms
            empty_response = "empty_response" in transforms

            if empty_response:
                obj = None
                json_ok = False
                parse_error = "empty_response"
            else:
                try:
                    obj = json.loads(cleaned)
                    json_ok = True
                    parse_error = None
                except json.JSONDecodeError as e:
                    obj = None
                    json_ok = False
                    parse_error = f"{e.__class__.__name__}: {e.msg} at line {e.lineno} col {e.colno}"

            schema = evaluate_schema(obj) if json_ok else {
                "schema_pass": False,
                "schema_fail_reasons": ["json_parse_failed"] if not empty_response else ["empty_response"],
            }

            result = {
                "episode_id": eid,
                "category": cat,
                "http_status": 200,
                "json_parse_ok": json_ok,
                "schema_conformance": schema.get("schema_pass", False),
                "schema_pass": schema.get("schema_pass", False),  # alias for back-compat
                "schema_fail_reasons": schema.get("schema_fail_reasons", []),
                "had_markdown_fences": had_fences,
                "had_prose_around_json": had_prose,
                "empty_response": empty_response,
                "transforms_applied": transforms,
                "fail_reason": (parse_error if not json_ok
                                else (";".join(schema.get("schema_fail_reasons", []))
                                      if not schema.get("schema_pass") else None)),
                "parse_error": parse_error,
                "latency_ms": int(round(latency * 1000)),
                "latency_s": round(latency, 3),
                "raw_output": raw_content,
                "raw_content_len": len(raw_content),
                "cleaned_len": len(cleaned),
                "raw_content_preview": raw_content[:300],
                "usage": full_resp.get("usage", {}),
            }
            status = "OK " if json_ok else "FAIL"
            schema_marker = "S" if result["schema_pass"] else "."
            fence_marker = "F" if had_fences else ("P" if had_prose else ".")
            print(f"[{i:>2}/50] {status} {schema_marker}{fence_marker} {latency:>6.2f}s {cat:<24s} {eid}")
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                err_body = str(e)
            result = {
                "episode_id": eid, "category": cat,
                "http_status": e.code,
                "json_parse_ok": False,
                "schema_conformance": False,
                "schema_pass": False,
                "schema_fail_reasons": [f"http_error:{e.code}"],
                "had_markdown_fences": False, "had_prose_around_json": False,
                "empty_response": False, "transforms_applied": [],
                "fail_reason": f"http_error:{e.code}",
                "parse_error": f"HTTP {e.code}: {err_body[:200]}",
                "latency_ms": None, "latency_s": None,
                "raw_output": "",
                "raw_content_len": 0, "cleaned_len": 0,
                "raw_content_preview": "", "usage": {},
            }
            print(f"[{i:>2}/50] ERR  http={e.code}  {eid}")
        except Exception as e:
            is_timeout = (e.__class__.__name__ in ("timeout", "TimeoutError")
                          or "timed out" in str(e).lower())
            fail_reason = "timeout" if is_timeout else f"exception:{e.__class__.__name__}"
            result = {
                "episode_id": eid, "category": cat,
                "http_status": None,
                "json_parse_ok": False,
                "schema_conformance": False,
                "schema_pass": False,
                "schema_fail_reasons": [fail_reason],
                "had_markdown_fences": False, "had_prose_around_json": False,
                "empty_response": False, "transforms_applied": [],
                "fail_reason": fail_reason,
                "parse_error": f"{e.__class__.__name__}: {e}",
                "latency_ms": None, "latency_s": None,
                "raw_output": "",
                "raw_content_len": 0, "cleaned_len": 0,
                "raw_content_preview": "", "usage": {},
            }
            print(f"[{i:>2}/50] ERR  exc={e.__class__.__name__}  {eid}")

        results.append(result)

    total_elapsed = time.monotonic() - t_total

    # write results.jsonl
    with RESULTS_PATH.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # aggregate metrics
    n = len(results)
    parse_ok = sum(1 for r in results if r["json_parse_ok"])
    schema_ok = sum(1 for r in results if r["schema_pass"])
    fenced = sum(1 for r in results if r["had_markdown_fences"])
    prose_wrapped = sum(1 for r in results if r.get("had_prose_around_json"))
    latencies_ms = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    if latencies_ms:
        latencies_sorted = sorted(latencies_ms)
        mean_lat_ms = mean(latencies_ms)
        p95_idx = max(0, int(0.95 * len(latencies_sorted)) - 1)
        p95_lat_ms = latencies_sorted[p95_idx]
        max_lat_ms = max(latencies_ms)
    else:
        mean_lat_ms = p95_lat_ms = max_lat_ms = float("nan")

    by_cat: dict[str, list] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)

    # Failure-mode counts
    failure_modes = {
        "markdown_fence_unstripped": 0,
        "truncated_json": 0,
        "missing_schema_field": 0,
        "empty_response": 0,
        "http_error": 0,
        "timeout": 0,
        "regex_grabbed_json_block": prose_wrapped,
        "schema_pass_after_postprocess": 0,
    }
    for r in results:
        pe = (r.get("parse_error") or "")
        if r.get("empty_response"):
            failure_modes["empty_response"] += 1
        if "Unterminated string" in pe or "Expecting value" in pe and r.get("raw_content_len", 0) > 1500:
            failure_modes["truncated_json"] += 1
        if r.get("fail_reason", "") and r["fail_reason"].startswith("http_error"):
            failure_modes["http_error"] += 1
        if r.get("fail_reason") == "timeout":
            failure_modes["timeout"] += 1
        if any(reason.startswith("missing_top_keys")
               or "_missing:" in reason
               for reason in r.get("schema_fail_reasons") or []):
            failure_modes["missing_schema_field"] += 1
        # markdown_fence_unstripped is conceptually "model emitted a fence we
        # COULDN'T strip"; with our regex it's effectively zero. Track the
        # weaker signal (model emitted any fence) separately.
        if r.get("had_markdown_fences") and not r["json_parse_ok"]:
            failure_modes["markdown_fence_unstripped"] += 1

    summary = {
        "total_episodes": n,
        "parse_ok": parse_ok,
        "parse_ok_pct": round(100.0 * parse_ok / n, 2),
        "schema_pass": schema_ok,
        "schema_pass_pct": round(100.0 * schema_ok / n, 2),
        "had_markdown_fences": fenced,
        "had_prose_around_json": prose_wrapped,
        "mean_latency_ms": round(mean_lat_ms, 1) if latencies_ms else None,
        "p95_latency_ms": round(p95_lat_ms, 1) if latencies_ms else None,
        "max_latency_ms": round(max_lat_ms, 1) if latencies_ms else None,
        "total_runtime_s": round(total_elapsed, 1),
        "by_category": {
            cat: {
                "n": len(rs),
                "parse_ok": sum(1 for r in rs if r["json_parse_ok"]),
                "schema_pass": sum(1 for r in rs if r["schema_pass"]),
            } for cat, rs in by_cat.items()
        },
        "failure_modes": failure_modes,
    }

    print()
    print("=" * 60)
    print("AGGREGATE METRICS")
    print("=" * 60)
    print(json.dumps(summary, indent=2))

    # append summary as last line of results.jsonl with marker
    with RESULTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"_summary": True, **summary}) + "\n")

    parse_pct = summary["parse_ok_pct"]
    schema_pct = summary["schema_pass_pct"]
    if parse_pct >= 95.0 and schema_pct >= 90.0:
        verdict = f"ADOPT-LOCAL — parse {parse_pct}% (>=95%) AND schema {schema_pct}% (>=90%)"
    elif parse_pct >= 80.0:
        verdict = f"ADOPT-WITH-CAVEATS — parse {parse_pct}% in 80-94% band (or schema below 90%)"
    else:
        verdict = f"STAY-ON-CLOUD — parse {parse_pct}% < 80%"
    print(f"\nVERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
