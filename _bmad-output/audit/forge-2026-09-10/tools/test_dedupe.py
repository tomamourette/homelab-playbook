#!/usr/bin/env python3
"""Self-test for dedupe.py — run before trusting any round's dedupe output.

Covers the failure modes hit while writing the tool on 2026-09-10:
- exact-string keys missed the same defect in two wordings           -> token-set similarity
- ISO timestamps left a stray token that sank similarity below cut   -> strip timestamps first, case-insensitive
- identical absence_of with different wording was not merged         -> ABSENCE buckets merge on absence_of
- template (.j2) vs rendered file never linked across subsystems     -> stem anchors
- over-merging distinct defects on the same file must NOT happen     -> negative case
Exit 0 on PASS, 1 on FAIL. Deterministic: same input -> identical output bytes.
"""
import importlib.util, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("dd", os.path.join(HERE, "dedupe.py"))
dd = importlib.util.module_from_spec(spec); spec.loader.exec_module(dd)

RAW = [
 {"id": "R1-P2-S4-001", "subsystem": "S4", "persona": "P2", "file": "/etc/coder.d/coder.env",
  "claim": "coder.env is 0644 (line 31) — world readable", "evidence": ["-rw-r--r--"], "severity": "high",
  "reproducer": "stat -c %a /etc/coder.d/coder.env"},
 {"id": "R1-P4-S4-007", "subsystem": "S4", "persona": "P4", "file": "/etc/coder.d/coder.env",
  "claim": "/etc/coder.d/coder.env mode 644 at 2026-09-10T08:00:00Z", "evidence": ["stat: 644"], "severity": "medium",
  "reproducer": "stat -c %a /etc/coder.d/coder.env"},
 {"id": "R1-P2-S4-009", "subsystem": "S4", "persona": "P2", "file": "/etc/coder.d/coder.env",
  "claim": "coder.env owned by coder:coder instead of root — wrong owner", "evidence": ["stat: coder coder"], "severity": "medium"},
 {"id": "R1-P4-S2-003", "subsystem": "S2", "persona": "P4", "file": "roles/forge-coder-host/templates/coder.env.j2",
  "claim": "template renders coder.env without an explicit mode so the file lands 0644", "evidence": ["no mode:"], "severity": "medium"},
 {"id": "R1-P3-S4-011", "subsystem": "S4", "persona": "P3", "file": None,
  "absence_of": "alerting on caddy certificate renewal failure", "claim": "nothing monitors cert renewal", "evidence": ["no rule"], "severity": "medium"},
 {"id": "R1-P6-S4-012", "subsystem": "S4", "persona": "P6", "file": None,
  "absence_of": "alerting on caddy certificate renewal failure", "claim": "Cert renewal failure would be silent — no alert exists", "evidence": ["journal only"], "severity": "low"},
]


def main():
    o = dd.dedupe(RAW); m = o["merged_from"]
    u001 = next(u for u in o["unique"] if u["id"] == "R1-P2-S4-001")
    checks = {
        "merge-two-wordings":      m.get("R1-P2-S4-001") == ["R1-P2-S4-001", "R1-P4-S4-007"],
        "merge-identical-absence": m.get("R1-P3-S4-011") == ["R1-P3-S4-011", "R1-P6-S4-012"],
        "no-overmerge-same-file":  len(m.get("R1-P2-S4-009", [])) == 1,
        "cross-subsystem-link":    any({"R1-P2-S4-001", "R1-P4-S2-003"} <= set(l[:2]) for l in o["links"]),
        "widest-severity-kept":    u001["severity_proposed"] == "high",
        "personas-union":          sorted(u001["personas"]) == ["P2", "P4"],
        "evidence-concatenated":   u001["evidence"] == ["-rw-r--r--", "stat: 644"],
        "unique-count":            o["stats"]["unique"] == 4,
    }
    # determinism: two subprocess runs must produce identical bytes
    inp = json.dumps(RAW)
    r1 = subprocess.run([sys.executable, os.path.join(HERE, "dedupe.py")], input=inp, capture_output=True, text=True).stdout
    r2 = subprocess.run([sys.executable, os.path.join(HERE, "dedupe.py")], input=inp, capture_output=True, text=True).stdout
    checks["deterministic"] = (r1 == r2) and len(r1) > 0
    for k, v in checks.items():
        print(f"  {k:<26} {'ok' if v else 'FAIL'}")
    ok = all(checks.values())
    print("SELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
