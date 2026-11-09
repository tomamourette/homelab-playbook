#!/usr/bin/env python3
"""Deterministic finding dedupe + root-cause linking for the Forge audit (plan §5).

Input : JSON array of raw findings (schema per plan §12; `file` may be null with `absence_of`).
Output: JSON object {unique: [...], merged_from: {id: [raw ids]}, links: [[id, id, why], ...]}

Rules
- key = (subsystem, file or "ABSENCE:"+absence_of, normalised claim)
- normalised claim: lowercase, strip line numbers / hashes / timestamps / quotes / whitespace runs,
  drop stopwords, keep first 12 significant tokens — so "coder.env is 0644 (line 31)" and
  "/etc/coder.d/coder.env mode 644" collide.
- merge keeps every evidence item, every persona, the widest severity (highest), earliest id.
- root-cause links: two unique findings are linked (not merged) when they share a normalised
  anchor token set (path stem, unit name, variable name) across DIFFERENT subsystems — the
  verifier sees the link and may judge them as one defect with two symptoms.
No LLM involvement; same input always yields the same output.
"""
import json, re, sys
from collections import defaultdict

SEV = {"critical": 4, "high": 3, "medium": 2, "low": 1, None: 0, "": 0}
STOP = set("the a an is are was were be been of to in on at for and or not no with by from that this it its as into via".split())
_line = re.compile(r"(?:[:#]|line\s+)\d+(?:-\d+)?|\bL\d+\b", re.I)
_hash = re.compile(r"\b[0-9a-f]{7,64}\b")
_time = re.compile(r"\d{4}-\d{2}-\d{2}(?:[t ]\d{2}(?::\d{2}){0,2}z?)?", re.I)   # full ISO stamp, case-insensitive (claims are lowercased)
_quote = re.compile(r"[`'\"“”‘’]")
_ws = re.compile(r"\s+")
_anchor = re.compile(r"(?:/[\w.\-]+)+|\b[\w\-]+\.(?:service|timer|tf|yml|yaml|sh|py|j2|env|conf)\b|\bvar\.[\w]+|\b[A-Z_]{4,}\b")


def tokens(f):
    s = (f.get("claim") or "").lower()
    s = _time.sub(" ", s); s = _line.sub(" ", s); s = _hash.sub(" ", s); s = _quote.sub("", s)   # timestamps first: _line would eat their :00 pieces
    s = re.sub(r"\b0?644\b", "0644", s); s = re.sub(r"\b0?600\b", "0600", s)
    out = set()
    for tok in _ws.sub(" ", s).strip().split(" "):
        tok = tok.strip(".,;:()[]{}—-")
        if len(tok) < 2 or tok in STOP: continue
        if "/" in tok: tok = tok.rsplit("/", 1)[-1]          # paths -> basename
        tok = re.sub(r"\.j2$", "", tok)                      # template stem == rendered file
        out.add(tok)
    return out


def location(f):
    if f.get("file"):
        return "FILE:" + re.sub(r"\.j2$", "", f["file"].rsplit("/", 1)[-1].lower())
    return "ABSENCE:" + _ws.sub(" ", (f.get("absence_of") or "").lower()).strip()


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0


def anchors(f):
    text = " ".join([f.get("file") or "", f.get("absence_of") or "", f.get("claim") or ""] + [str(e) for e in f.get("evidence", [])])
    out = set()
    for a in _anchor.findall(text):
        a = a.lower().rsplit("/", 1)[-1]
        a = re.sub(r"\.j2$", "", a)
        if len(a) > 3: out.add(a)
    return out


def dedupe(raw, sim=0.34):
    # bucket by (subsystem, location); inside a bucket cluster by claim-token similarity;
    # ABSENCE buckets merge on identical absence_of regardless of wording (that IS the claim).
    buckets = defaultdict(list)
    for f in raw:
        buckets[(f.get("subsystem", ""), location(f))].append(f)
    clusters = []
    for (sub, loc), fs in buckets.items():
        fs = sorted(fs, key=lambda x: x.get("id", ""))
        if loc.startswith("ABSENCE:"):
            clusters.append(fs); continue
        groups = []
        for f in fs:
            tf = tokens(f)
            for g in groups:
                if jaccard(tf, g["tok"]) >= sim:
                    g["items"].append(f); g["tok"] |= tf; break
            else:
                groups.append({"tok": set(tf), "items": [f]})
        clusters.extend(g["items"] for g in groups)
    unique, merged_from = [], {}
    for fs in clusters:
        base = dict(fs[0])
        base["personas"] = sorted({x.get("persona", "") for x in fs} - {""})
        base["evidence"] = [e for x in fs for e in (x.get("evidence") or [])]
        base["reproducers"] = sorted({x.get("reproducer") for x in fs if x.get("reproducer")})
        base["severity_proposed"] = max((x.get("severity") for x in fs), key=lambda s: SEV.get((s or "").lower(), 0))
        base.pop("severity", None); base.pop("persona", None)
        merged_from[base["id"]] = [x.get("id") for x in fs]
        unique.append(base)
    links = []
    anc = {u["id"]: anchors(u) for u in unique}
    for i, a in enumerate(unique):
        for b in unique[i + 1:]:
            if a.get("subsystem") == b.get("subsystem"):
                continue
            shared = anc[a["id"]] & anc[b["id"]]
            specific = {s for s in shared if "." in s or s.startswith("var.")}   # file stems / unit names / vars
            if specific or len(shared) >= 2:
                links.append([a["id"], b["id"], "shared anchors: " + ", ".join(sorted(shared)[:5])])
    return {"unique": unique, "merged_from": merged_from, "links": links,
            "stats": {"raw": len(raw), "unique": len(unique), "links": len(links)}}


if __name__ == "__main__":
    data = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else json.load(sys.stdin)
    if isinstance(data, dict) and "findings" in data:
        data = data["findings"]
    print(json.dumps(dedupe(data), indent=2, ensure_ascii=False))
