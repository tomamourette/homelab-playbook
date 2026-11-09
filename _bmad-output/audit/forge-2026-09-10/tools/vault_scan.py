#!/usr/bin/env python3
"""Scan files for Ansible-vault VALUES, distinguishing credentials from identifiers (plan §7/§8.2).

Never prints a value. Output is per-file counts by KEY NAME and a verdict.

Classification (by key name, then by value shape):
  CREDENTIAL : name matches password|passwd|secret|token|apikey|api_key|authkey|private|key$  (unless identifier override)
  IDENTIFIER : name matches host|hostname|email|url|user|username|id$|zone_id|domain|channel, or the value is an IP address
Identifiers are reported but do not fail the scan; credentials do.

Usage:
  vault_scan.py [--vault PATH] [--pass PATH] [--min-len 8] [--redact] PATH...
  PATH may be files or directories (recursed; .git skipped). Exit 1 if any CREDENTIAL value is found.
  --redact rewrites matching files in place replacing every vault value (credential or identifier) with <REDACTED-VAULT:name>.
"""
import argparse, ipaddress, os, re, subprocess, sys, yaml

CRED = re.compile(r"(password|passwd|secret|token|api_?key|auth_?key|private|_key$)", re.I)
IDENT = re.compile(r"(host|hostname|email|url|user(name)?$|_id$|zone_id|domain|channel|slug)", re.I)


def load_vault(vault, passfile):
    out = subprocess.run(["ansible-vault", "view", "--vault-password-file", passfile, vault], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"vault decrypt failed: {out.stderr.strip()[:200]}")
    return yaml.safe_load(out.stdout) or {}


def classify(name, value):
    v = str(value)
    try:
        ipaddress.ip_address(v); return "identifier"
    except ValueError:
        pass
    if IDENT.search(name) and not re.search(r"(password|secret|token|api_?key|auth_?key)", name, re.I):
        return "identifier"
    if CRED.search(name):
        return "credential"
    return "identifier" if "@" in v or v.startswith(("http://", "https://")) else "credential"


def iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d != ".git"]
                for f in files:
                    yield os.path.join(root, f)
        elif os.path.isfile(p):
            yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--vault", default="/home/developer/workspace/homelab/homelab-infra/ansible/inventories/homelab/group_vars/vault.yml")
    ap.add_argument("--pass", dest="passfile", default="/home/developer/workspace/homelab/homelab-infra/ansible/.vault_pass")
    ap.add_argument("--min-len", type=int, default=8)
    ap.add_argument("--redact", action="store_true")
    a = ap.parse_args()
    vault = {k: str(v) for k, v in load_vault(a.vault, a.passfile).items() if isinstance(v, (str, int)) and len(str(v)) >= a.min_len}
    kinds = {k: classify(k, v) for k, v in vault.items()}
    cred_hit = False; scanned = 0
    for path in iter_files(a.paths):
        try:
            data = open(path, "rb").read()
        except OSError:
            continue
        scanned += 1
        text = data.decode("utf-8", errors="replace")
        hits = {k: text.count(v) for k, v in vault.items() if v in text}
        if not hits:
            continue
        for k, n in sorted(hits.items()):
            kind = kinds[k]
            print(f"{'CREDENTIAL' if kind == 'credential' else 'identifier':<10} {n:>4}x {k:<36} {path}")
            if kind == "credential":
                cred_hit = True
        if a.redact:
            for k in hits:
                text = text.replace(vault[k], f"<REDACTED-VAULT:{k}>")
            open(path, "w", encoding="utf-8").write(text)
    print(f"scanned {scanned} file(s); credential values found: {'YES' if cred_hit else 'no'}")
    return 1 if cred_hit else 0


if __name__ == "__main__":
    sys.exit(main())
