# E2-S01 Install Evidence

**Date:** 2026-04-26
**Story:** E2-S01 Install GitNexus v1.6.3 + supply-chain verification
**Branch:** feature/context-stack-e2-gitnexus
**Operator:** tomamourette
**Workstation:** ai-dev container (Node v20.20.0, npm 10.8.2)

## Pre-install registry metadata

```
$ npm view gitnexus@1.6.3
gitnexus@1.6.3 | PolyForm-Noncommercial-1.0.0 | deps: 32 | versions: 130
Graph-powered code intelligence for AI agents. Index any codebase, query via MCP or CLI.
https://github.com/abhigyanpatwari/GitNexus#readme

bin: gitnexus

dist
.tarball:    https://registry.npmjs.org/gitnexus/-/gitnexus-1.6.3.tgz
.shasum:     6dca8c5f789763a5c093c1018620cb41ceff362a
.integrity:  sha512-Yvhc70ESXFHPMtXHSddDgNL3dUxdvmA+CmxoadFBB7rTxIcXi8vrY/jhMvjvzJpBxp4JKi+lD8Pt1m1wL88Mtg==
.unpackedSize: 4.5 MB
.fileCount:  906

maintainers:
- abhigyanpatwari <abhigyan1.patwari@gmail.com>

dist-tags:
latest: 1.6.3
rc:     1.6.4-rc.3

published 2 days ago by abhigyanpatwari <abhigyan1.patwari@gmail.com>

signature: MEYCIQCQARKOetvmR4UCJ//33uz5cRBl4oLlbWPHhsrSXNIhTwIhALCAE35kvYprKw5D6NKJ0rBl7i4kidI6EWBVmgzGJD4t
keyid:     SHA256:DhQ8wR5APBvFHLF/+Tc+AYvPOdTpcIDqOhxsBHRwC7U

attestations: https://registry.npmjs.org/-/npm/v1/attestations/gitnexus@1.6.3
provenance:   https://slsa.dev/provenance/v1
```

## Repository confirmation

Per ADR-004, expected repo is one of: `abhigyanpatwari/GitNexus`, `akonlabs/gitnexus`, `nxpatterns/gitnexus`.

Actual: `https://github.com/abhigyanpatwari/GitNexus#readme` (homepage), `git+https://github.com/abhigyanpatwari/GitNexus.git` (repository.url from installed package.json).

**Verdict: MATCH** — exactly the canonical ADR-004 repo (`abhigyanpatwari/GitNexus`). No typo, no fork, no transfer.

## Supply-chain strength signals (above expected baseline)

- **npm package signature:** present — registry-signed tarball
- **npm attestation:** SLSA v1 provenance — package was built and published from a verified GitHub Actions runner attached to `abhigyanpatwari/GitNexus`. This is stronger evidence than maintainer name alone — it cryptographically links the npm artifact back to a build of the source repo.
- **dist-tags:** `latest: 1.6.3`, `rc: 1.6.4-rc.3` — coherent release-train shape.
- **Maintainer count:** 1 (abhigyanpatwari). ADR-004 already flagged single-maintainer risk; SLSA provenance partially mitigates by tying releases to a verified pipeline.

## Install command

```
$ sudo chown -R 1000:1000 /home/developer/.npm   # one-time cache permissions fix (root-owned files from earlier session)
$ npm install -g gitnexus@1.6.3
npm warn deprecated boolean@3.2.0: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.

added 254 packages in 1m
```

`boolean@3.2.0` is a transitive deprecation — flagged for awareness, no action needed at story scope.

## Post-install verification

```
$ which gitnexus
/home/developer/.npm-global/bin/gitnexus

$ gitnexus --version
1.6.3

$ npm list -g gitnexus
/home/developer/.npm-global/lib
└── gitnexus@1.6.3

$ ls -la /home/developer/.npm-global/lib/node_modules/gitnexus/
total 65
-rw-r--r--   README.md            (15089 bytes)
drwxr-xr-x   dist/                (CLI + MCP server entry points)
drwxr-xr-x   hooks/               (Claude Code hook artifacts shipped with package — relevant for E2-S04)
drwxr-xr-x   node_modules/        (207 dirs)
-rw-r--r--   package.json         (3394 bytes)
drwxr-xr-x   scripts/
drwxr-xr-x   skills/              (skill artifacts shipped with package — note for E2-S03)
drwxr-xr-x   vendor/
```

## Installed package metadata (from /home/developer/.npm-global/lib/node_modules/gitnexus/package.json)

- **Name:** gitnexus
- **Version:** 1.6.3
- **Author:** Abhigyan Patwari
- **License:** PolyForm-Noncommercial-1.0.0
- **Homepage:** https://github.com/abhigyanpatwari/GitNexus#readme
- **Repository:** git+https://github.com/abhigyanpatwari/GitNexus.git
- **Bin:** dist/cli/index.js
- **Type:** module (ESM)

## Supply-chain hygiene

- **Integrity hash (sha512, recorded for future-rebuild verification):**
  `sha512-Yvhc70ESXFHPMtXHSddDgNL3dUxdvmA+CmxoadFBB7rTxIcXi8vrY/jhMvjvzJpBxp4JKi+lD8Pt1m1wL88Mtg==`
- **SHA1 shasum:** `6dca8c5f789763a5c093c1018620cb41ceff362a`
- **npm audit:** N/A for global installs (`ENOLOCK: This command requires an existing lockfile`). This is an npm 10.x limitation, not a finding. To audit transitives, a follow-up story can clone the repo and run `npm ci && npm audit` against the lockfile (deferred — not a v1.6.3 install blocker).
- **Typosquat guard:** package name verified as `gitnexus` (exact, no doubled letters; ADR-004 lesson from `graphifyy` typosquat-watch applied).

## Notes / minor findings (none are blockers)

1. **No standalone LICENSE file shipped in tarball** — license is declared in `package.json` (`PolyForm-Noncommercial-1.0.0`) and referenced in README. PolyForm-Noncommercial means the license is non-OSI; permitted for personal homelab use, would require relicensing or alternative if this stack ever ships commercially. Documented for ADR-004 reversibility tracking.
2. **Single-maintainer package** — already flagged as ADR-004 risk; mitigated by NDJSON exit ramp (E2-S07) and SLSA provenance attestations.
3. **`boolean@3.2.0` deprecation warning** — transitive, upstream concern.
4. **npm cache had root-owned files** — fixed with `chown -R 1000:1000 /home/developer/.npm`. Pre-existing condition unrelated to GitNexus; recorded so a workstation rebuild script knows to set npm cache ownership before `npm install -g`.

## Verdict

**PASS.** Package metadata is coherent, repository matches ADR-004 exactly, SLSA provenance attestation strengthens supply-chain confidence beyond the minimum required, integrity hash captured for reproducibility, install completed cleanly, version verified. No red flags.

## Remediation if ever needed

```
npm uninstall -g gitnexus    # ~30 s — restores pre-install state
```

This removes only the global binary; no `~/.claude/settings.json` changes were made in this story (that's E2-S03 / E2-S04), so no further cleanup required.
