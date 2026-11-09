# Fix F — DNS measurement log (harness, production image)

Date 2026-09-10. Harness `forge-dns-harness`, image `pihole/pihole:2024.07.0`,
listener `127.0.0.1:5399` (udp+tcp). All queries:
`dig @127.0.0.1 -p 5399 +noall +comments +answer <type> <name>`.

## Harness fidelity

| item | production (CT 101) | harness |
|---|---|---|
| image | pihole/pihole:2024.07.0 | same |
| FTL | v5.25.2 | v5.25.2 |
| dnsmasq | pi-hole-v2.90+1 | pi-hole-v2.90+1 |
| 01-pihole.conf | — | byte-identical (non-comment/non-blank diff empty) |
| upstreams | 8.8.8.8;8.8.4.4 | same |
| 02-homelab.conf / 05-forge.conf / custom.list | — | verbatim copies |
| /etc/dnsmasq.conf | `conf-dir=/etc/dnsmasq.d` | same + extra `user=pihole` line |

**conf-dir line (verbatim, production):** `conf-dir=/etc/dnsmasq.d`
— note: NO `,*.conf` filter.

Deviations: harness adds `--cap-add SETFCAP --cap-add DAC_OVERRIDE` (without
them FTL could not bind UDP/IPv4 under docker 29.3.1 on the workbench) and
mounts `/etc/pihole` from a local rw dir (production binds
`/opt/appdata/dns-pihole/config`). Neither affects name-resolution semantics.

CORRECTION (round 4): an earlier version of this file said the harness
`/etc/dnsmasq.conf` carries an extra `user=pihole` line "that production does
not, because production FTL runs as root". The first half is right, the second
half was WRONG. Measured read-only on CT 101 2026-09-10:

    ssh root@192.168.50.194 "docker exec pihole ps -o pid,user,uid,comm -C pihole-FTL"
        PID USER       UID COMMAND
     253388 pihole     999 pihole-FTL

Production pihole-FTL runs as uid 999 (`pihole`), exactly as the harness does,
so `docker exec -u pihole ... pkill -TERM -x pihole-FTL` is valid on both.

## T0 — baseline, production config verbatim (defect reproduced)

    A     forge.bi-services.be           NOERROR  qr aa rd ra  ANSWER=1  A 192.168.50.167
    AAAA  forge.bi-services.be           NXDOMAIN qr rd ra     ANSWER=0
    A     x1.forge.bi-services.be        NOERROR  qr aa rd ra  ANSWER=1  A 192.168.50.167
    AAAA  x1.forge.bi-services.be        NXDOMAIN qr rd ra     ANSWER=0
    A     hermes.bi-services.be          NOERROR  qr aa rd ra  ANSWER=1  A 192.168.50.194
    AAAA  hermes.bi-services.be          NOERROR  qr rd ra     ANSWER=0   <- correct NODATA
    A     gemma.bi-services.be           NXDOMAIN qr rd ra     ANSWER=0   <- C3
    A     nonexistent.bi-services.be     NXDOMAIN qr rd ra     ANSWER=0

C1 and C3 both reproduce exactly. Harness is valid.

## T1 — addn-hosts for specific names (file OUTSIDE conf-dir, /etc/pihole/forge.hosts)

Config: baseline `address=` + `addn-hosts=/etc/pihole/forge.hosts`.

    A     forge.bi-services.be           NOERROR aa ANSWER=1 A 192.168.50.167
    AAAA  forge.bi-services.be           NOERROR    ANSWER=0   FIXED
    A     gemma.bi-services.be           NOERROR aa ANSWER=1 A 192.168.50.201
    AAAA  gemma.bi-services.be           NOERROR    ANSWER=0   FIXED
    (ct-forge-01/.202, ct-saply-ai/.203, ct-crypto-quant/.204 identical shape)
    A     x1.forge.bi-services.be        NOERROR aa ANSWER=1 A 192.168.50.167
    AAAA  x1.forge.bi-services.be        NXDOMAIN   ANSWER=0   STILL BROKEN
    A     hermes.bi-services.be          NOERROR aa ANSWER=1 A 192.168.50.194
    A     nonexistent.bi-services.be     NXDOMAIN   ANSWER=0

Verdict: fixes C3 and the forge APEX AAAA. Does NOT fix wildcard-label AAAA.

### T1b — precedence probe (hosts entry with a DIFFERENT ip than address=)

hosts said `192.168.50.99 forge.bi-services.be`, config said `.167`:

    A forge.bi-services.be     NOERROR aa ANSWER=1 A 192.168.50.99   <- hosts WINS
    A x1.forge.bi-services.be  NOERROR aa ANSWER=1 A 192.168.50.167  <- wildcard still applies

Confirms: addn-hosts overrides address= for the exact name; address= still
covers every other label in the subtree.

## T2 — conf-dir parsing risk

### T2a — hosts file placed directly in /etc/dnsmasq.d as 05-forge.hosts

    $ docker exec forge-dns-harness pihole-FTL dnsmasq-test
    dnsmasq: bad option at line 2 of /etc/dnsmasq.d/05-forge.hosts

    $ docker logs --tail 40 forge-dns-harness
    Stopping pihole-FTL
    pihole-FTL: no process found      (repeating — s6 crash-restart loop)

FTL never starts. DNS is DOWN for the whole LAN. **non_conf_file_parsed_as_config = TRUE.**
This is the trap the brief predicted; `conf-dir=/etc/dnsmasq.d` has no `,*.conf`
filter, so every regular file in that directory is parsed as dnsmasq config.

### T2b — hosts file in subdirectory /etc/dnsmasq.d/forge/05-forge.hosts

    $ docker exec forge-dns-harness pihole-FTL dnsmasq-test
    dnsmasq: syntax check OK.

    A hermes.bi-services.be  NOERROR aa ANSWER=1 A 192.168.50.194
    A gemma.bi-services.be   NOERROR aa ANSWER=1 A 192.168.50.201
    AAAA gemma...            NOERROR    ANSWER=0

FTL starts, hosts file loads via addn-hosts. **subdir_skipped_by_conf_dir = TRUE.**

## T3 — wildcard AAAA via `server=/forge.bi-services.be/#`

Public zone precondition (via 8.8.8.8): `forge`, `x1.forge`, `y2.forge` all
A=192.168.50.167, AAAA NOERROR/ANSWER=0. NS = anuj/elisa.ns.cloudflare.com.

### T3a — address= + server=/#/, no hosts file

    A     forge.bi-services.be       NOERROR qr aa rd ra ANSWER=1 A 192.168.50.167
    A     x1.forge.bi-services.be    NOERROR qr aa rd ra ANSWER=1 A 192.168.50.167
    AAAA  forge.bi-services.be       NOERROR qr rd ra    ANSWER=0
    AAAA  x1.forge.bi-services.be    NOERROR qr rd ra    ANSWER=0
    AAAA  y2.forge.bi-services.be    NOERROR qr rd ra    ANSWER=0
    TXT   x1.forge.bi-services.be    NOERROR qr rd ra    ANSWER=0
    A     hermes...                  NOERROR aa ANSWER=1 A 192.168.50.194
    A     nonexistent...             NXDOMAIN
    A     gemma...                   NXDOMAIN  (still needs the hosts file)

A precedence preserved (`aa` proves the answer is local, not forwarded).
AAAA NODATA achieved — but by FORWARDING to the public zone.

### T3b — combined (address= + server=/#/ + addn-hosts subdir)

All of REQ1/REQ2/REQ3 green with working upstream. Full matrix in T7 below.

## T4 — upstream unreachable (PIHOLE_DNS_=192.0.2.1), dig default 5s x3 tries

### T4 with the T3 (`server=/#/`) design

    A     forge.bi-services.be       NOERROR         ANSWER=1 elapsed=18ms  A 192.168.50.167
    A     x1.forge.bi-services.be    NOERROR         ANSWER=1 elapsed=18ms  A 192.168.50.167
    A     gemma.bi-services.be       NOERROR         ANSWER=1 elapsed=18ms  A 192.168.50.201
    A     hermes.bi-services.be      NOERROR         ANSWER=1 elapsed=18ms  A 192.168.50.194
    AAAA  hermes.bi-services.be      NOERROR         ANSWER=0 elapsed=19ms
    AAAA  gemma.bi-services.be       NOERROR         ANSWER=0 elapsed=8ms
    AAAA  forge.bi-services.be       no servers reached       elapsed=15036ms
    AAAA  x1.forge.bi-services.be    no servers reached       elapsed=15034ms

All A records survive. AAAA for the forge subtree gets NO ANSWER AT ALL (query
silently dropped, dig gives up after 15s). This is the cost of mechanism (b).

### T4-FINAL with the chosen design (empty `address=`, no forwarding)

    A     forge.bi-services.be       NOERROR ANSWER=1 elapsed=20ms A 192.168.50.167
    AAAA  forge.bi-services.be       NOERROR ANSWER=0 elapsed=17ms
    A     x1.forge.bi-services.be    NOERROR ANSWER=1 elapsed=17ms A 192.168.50.167
    AAAA  x1.forge.bi-services.be    NOERROR ANSWER=0 elapsed=18ms
    A     gemma.bi-services.be       NOERROR ANSWER=1 elapsed=19ms A 192.168.50.201
    AAAA  gemma.bi-services.be       NOERROR ANSWER=0 elapsed=18ms
    A     hermes.bi-services.be      NOERROR ANSWER=1 elapsed=18ms A 192.168.50.194
    AAAA  hermes.bi-services.be      NOERROR ANSWER=0 elapsed=18ms

FULLY IMMUNE to upstream failure. Every answer ~18ms. Strictly better than T3.

## T6a — CHOSEN MECHANISM: bare `address=/forge.bi-services.be/` (no IP)

Config:

    address=/forge.bi-services.be/192.168.50.167
    address=/forge.bi-services.be/
    addn-hosts=/etc/dnsmasq.d/forge/05-forge.hosts

    A     forge.bi-services.be       NOERROR qr aa rd ra ANSWER=1 A 192.168.50.167
    AAAA  forge.bi-services.be       NOERROR qr rd ra    ANSWER=0
    A     x1.forge.bi-services.be    NOERROR qr aa rd ra ANSWER=1 A 192.168.50.167
    AAAA  x1.forge.bi-services.be    NOERROR qr rd ra    ANSWER=0

**Proof it is answered locally, not forwarded** — FTL query log:

    $ docker exec forge-dns-harness grep -i t6probe /var/log/pihole/pihole.log
    query[AAAA] t6probe.forge.bi-services.be from 172.17.0.1
    config t6probe.forge.bi-services.be is NODATA-IPv6
    query[TXT] t6probe.forge.bi-services.be from 172.17.0.1
    config t6probe.forge.bi-services.be is NODATA

`config ... is NODATA-IPv6` = served from config. No `forwarded ... to 8.8.8.8`
line exists for these queries. No synthetic IPv6 address is returned.

Note: the dnsmasq man text claims a bare `address=/d/` returns NXDOMAIN for the
domain and its subdomains. On this build (pi-hole-v2.90+1), when paired with an
`address=/d/<ip>` for the same domain, the measured behaviour is NODATA for the
non-matching types and the A record still served. Measured, not assumed.

### T6a-ORDER — order independence

Reversed (`address=/forge.bi-services.be/` written BEFORE the `<ip>` line):
identical results (A .167 with aa, AAAA NOERROR/0). Order does not matter.

## T7 — FINAL DESIGN, full matrix (working upstream)

REQ1 apex + wildcard labels:

    A    forge.bi-services.be             NOERROR aa ANSWER=1 A 192.168.50.167
    AAAA forge.bi-services.be             NOERROR    ANSWER=0
    A    x1.forge.bi-services.be          NOERROR aa ANSWER=1 A 192.168.50.167
    AAAA x1.forge.bi-services.be          NOERROR    ANSWER=0
    A    y2.forge.bi-services.be          NOERROR aa ANSWER=1 A 192.168.50.167
    AAAA y2.forge.bi-services.be          NOERROR    ANSWER=0
    A    deep.a.b.forge.bi-services.be    NOERROR aa ANSWER=1 A 192.168.50.167
    AAAA deep.a.b.forge.bi-services.be    NOERROR    ANSWER=0

REQ3 hermes regression guard:

    A    hermes.bi-services.be            NOERROR aa ANSWER=1 A 192.168.50.194
    AAAA hermes.bi-services.be            NOERROR    ANSWER=0

T5 negative controls — nothing outside the forge subtree and the five names moved:

    A    nonexistent.bi-services.be       NXDOMAIN ANSWER=0
    AAAA nonexistent.bi-services.be       NXDOMAIN ANSWER=0
    A    notforge.bi-services.be          NXDOMAIN ANSWER=0   (no prefix bleed)
    A    forgex.bi-services.be            NXDOMAIN ANSWER=0   (no suffix bleed)
    A    grafana.bi-services.be           NOERROR aa ANSWER=1 A 192.168.50.194
    AAAA grafana.bi-services.be           NOERROR    ANSWER=0
    A    traefik.bi-services.be           NOERROR aa ANSWER=1 A 192.168.50.194
    A    example.com                      NOERROR ANSWER=2 A 104.20.23.154|A 172.66.147.243
    AAAA example.com                      NOERROR ANSWER=2 AAAA 2606:4700:10::6814:179a|...
    TXT  x1.forge.bi-services.be          NOERROR ANSWER=0
    MX   forge.bi-services.be             NOERROR ANSWER=0

## T10 — FINAL DESIGN with the real Terraform IPs

    A    forge.bi-services.be             NOERROR aa ANSWER=1 A 192.168.50.167
    AAAA forge.bi-services.be             NOERROR    ANSWER=0
    A    gemma.bi-services.be             NOERROR aa ANSWER=1 A 192.168.50.194
    AAAA gemma.bi-services.be             NOERROR    ANSWER=0
    A    ct-forge-01.bi-services.be       NOERROR aa ANSWER=1 A 192.168.50.167
    AAAA ct-forge-01.bi-services.be       NOERROR    ANSWER=0
    A    ct-saply-ai.bi-services.be       NOERROR aa ANSWER=1 A 192.168.50.164
    AAAA ct-saply-ai.bi-services.be       NOERROR    ANSWER=0
    A    ct-crypto-quant.bi-services.be   NOERROR aa ANSWER=1 A 192.168.50.165
    AAAA ct-crypto-quant.bi-services.be   NOERROR    ANSWER=0
    A    x1.forge.bi-services.be          NOERROR aa ANSWER=1 A 192.168.50.167
    AAAA x1.forge.bi-services.be          NOERROR    ANSWER=0
    A    hermes.bi-services.be            NOERROR aa ANSWER=1 A 192.168.50.194
    AAAA hermes.bi-services.be            NOERROR    ANSWER=0
    A    nonexistent.bi-services.be       NXDOMAIN   ANSWER=0

IPs sourced from terraform/envs/homelab/generated/pihole-custom.list
(lines 9, 11, 14, 18) and outputs.tf:137,149-151.

## T8/T9 — reload semantics

T8 hosts-file change (gemma .201 -> .222):

    edit file, wait 5s, no signal   -> still 192.168.50.201  (no inotify on addn-hosts)
    pkill -HUP -x pihole-FTL        -> 192.168.50.222        (SIGHUP re-reads hosts)

FTL log after SIGHUP:

    read /etc/hosts - 18 names
    read /etc/dnsmasq.d/forge/05-forge.hosts - 5 names
    read /etc/pihole/custom.list - 37 names
    read /etc/pihole/local.list - 0 names

T9 config-file change (`address=/sighuptest.bi-services.be/192.168.50.77`):

    add line, pkill -HUP            -> A sighuptest... NXDOMAIN   (SIGHUP ignores config)
    pkill -TERM (s6 re-exec)        -> A sighuptest... NOERROR aa ANSWER=1 A 192.168.50.77

Conclusion: **config changes require the full FTL re-exec** (the role's existing
`pkill -TERM -x pihole-FTL` + s6 restart). Hosts-only changes need only SIGHUP,
but the re-exec also covers them and is the already-proven-safe path.

## Terraform vs live custom.list (confirms C3)

    GENERATED-ONLY  192.168.50.164 ct-saply-ai.bi-services.be
    GENERATED-ONLY  192.168.50.165 ct-crypto-quant.bi-services.be
    GENERATED-ONLY  192.168.50.167 ct-forge-01.bi-services.be
    GENERATED-ONLY  192.168.50.167 forge.bi-services.be
    GENERATED-ONLY  192.168.50.194 gemma.bi-services.be
    LIVE-ONLY       192.168.50.194 hermes.bi-services.be   <- would be DELETED

## Chosen design

`/opt/appdata/dns-pihole/dnsmasq.d/05-forge.conf` (-> `/etc/dnsmasq.d/05-forge.conf`):

    address=/forge.bi-services.be/192.168.50.167
    address=/forge.bi-services.be/
    addn-hosts=/etc/dnsmasq.d/forge/05-forge.hosts

`/opt/appdata/dns-pihole/dnsmasq.d/forge/05-forge.hosts`
(-> `/etc/dnsmasq.d/forge/05-forge.hosts`), mode 0644:

    192.168.50.167 forge.bi-services.be
    192.168.50.194 gemma.bi-services.be
    192.168.50.167 ct-forge-01.bi-services.be
    192.168.50.164 ct-saply-ai.bi-services.be
    192.168.50.165 ct-crypto-quant.bi-services.be

Rejected: `server=/forge.bi-services.be/#` (works, but AAAA then depends on
upstream reachability AND on the public Cloudflare zone continuing to hold
private-IP records — 15s black hole when upstream is down, T4).
Rejected: `address=/.../::`, global filter-AAAA — excluded by requirements.

## Harness left running

    container  forge-dns-harness
    image      pihole/pihole:2024.07.0
    port       127.0.0.1:5399 (udp+tcp)
    config_dir /tmp/claude-1000/-home-developer-workspace-homelab/c5e9405f-f536-4cc5-a082-5b9f76b12392/scratchpad/forge-dns-f/harness/dnsmasq.d
    reload     /tmp/claude-1000/-home-developer-workspace-homelab/c5e9405f-f536-4cc5-a082-5b9f76b12392/scratchpad/forge-dns-f/harness/reload.sh
    query      /tmp/claude-1000/-home-developer-workspace-homelab/c5e9405f-f536-4cc5-a082-5b9f76b12392/scratchpad/forge-dns-f/harness/q.sh <TYPE> <NAME>
    syntax     docker exec forge-dns-harness pihole-FTL dnsmasq-test

---

# ROUND 4 measurements (harness rebuilt from scratch 2026-09-10 12:31)

Container `forge-dns-harness` was `docker rm -f`'d and recreated from a fresh
read-only capture of CT 101's four drop-ins, /etc/dnsmasq.conf, custom.list and
local.list (md5s identical to the round-1 capture). Baseline reproduced C1 and
C3 exactly:

    A     forge.bi-services.be    NOERROR qr aa rd ra ANSWER=1 A 192.168.50.167
    AAAA  forge.bi-services.be    NXDOMAIN qr rd ra   ANSWER=0
    A     gemma.bi-services.be    NXDOMAIN qr rd ra   ANSWER=0
    AAAA  hermes.bi-services.be   NOERROR qr rd ra    ANSWER=0
    PTR   192.168.50.194          NOERROR aa          alertmanager.bi-services.be.
    PTR   .167 / .164 / .165      (no answer)

## R4-PTR — where the addn-hosts= line is declared decides the reverse zone

Identical records, identical address= pair; only the declaring file moved.

  Layout A — `addn-hosts=` inside 05-forge.conf (round-3 design):
      FTL: read /etc/dnsmasq.d/forge/05-forge.hosts - 5 names
           read /etc/pihole/custom.list - 37 names
      dig -x 192.168.50.194 -> gemma.bi-services.be         <-- CHANGED
      dig -x .167/.164/.165 -> forge / ct-saply-ai / ct-crypto-quant  (added)

  Layout B — `addn-hosts=` alone in 00-forge-hosts.conf (ADOPTED):
      FTL: read /etc/pihole/custom.list - 37 names
           read /etc/dnsmasq.d/forge/05-forge.hosts - 5 names
      dig -x 192.168.50.194 -> alertmanager.bi-services.be  <-- UNCHANGED
      dig -x .167/.164/.165 -> forge / ct-saply-ai / ct-crypto-quant  (added)

  Forward resolution under Layout B, all NOERROR: forge / x1.forge /
  forge-dns-probe.forge / deep.a.b.forge A=192.168.50.167 with aa and AAAA
  ANSWER=0; gemma .194, ct-forge-01 .167, ct-saply-ai .164, ct-crypto-quant
  .165, all AAAA ANSWER=0; hermes A .194 + AAAA ANSWER=0; alertmanager .194;
  grafana .194 + AAAA ANSWER=0; traefik .194; TXT x1.forge ANSWER=0; MX forge
  ANSWER=0; nonexistent / notforge / forgex NXDOMAIN. Identical to Layout A.

  VERDICT: adopt Layout B. Three rendered files, PTR side effect eliminated.

## R4-DANGLING — a missing addn-hosts target is tolerated, NOT a crash loop

    docker exec forge-dns-harness pihole-FTL dnsmasq-test
    dnsmasq: syntax check OK.        rc=0
    (after restart) ps -C pihole-FTL -> 243 pihole pihole-FTL   [alive]
    pihole.log: failed to load names from /etc/dnsmasq.d/forge/05-forge.hosts:
                No such file or directory
    A forge=192.168.50.167  hermes=192.168.50.194  alertmanager=192.168.50.194
    A gemma=NXDOMAIN   (only the 5 hosts names are lost)

  The round-3 comment claiming a crash loop was WRONG and has been rewritten.
  Consequence for the role: the syntax gate CANNOT detect a dangling
  addn-hosts=; only the per-name dig verification can.

## R4-OUTAGE — cost of the FTL re-exec, re-measured 3x at 50 ms resolution

  s6-svc -u then `docker exec -u pihole ... pkill -TERM -x pihole-FTL`, while a
  50 ms loop dug hermes with +time=1 +tries=1:

    run 1: 296 probes, 1 failed, next success 1.072 s after the failing probe
    run 2: 304 probes, 1 failed, next success 1.063 s
    run 3: 303 probes, 1 failed, next success 1.073 s

  Exactly one missed probe each time. Round 3 measured 1.130 s on the previous
  harness. The role and playbook now quote "~1.1 s (measured: exactly one 50 ms
  probe missed per re-exec, 1.06-1.13 s ...)" instead of "sub-second".

## R4-ROLLBACK — the five states, proven end-to-end through the real role

  Harness `forge-dns-harness-iac` (same image, port 5398, its own conf dir),
  driven by the actual role via a localhost play. "gate fails" = an UNRELATED
  09-unrelated-bad.conf dropped into the conf dir.

  RUN A   fresh host, nothing pre-exists, gate OK
          -> plan: all three `remove`; snapshot skipped for the two new files,
             taken for the pre-existing 05-forge.conf. 6 changed. Play OK.
  RUN A2  immediate re-run -> plan: all three `leave`; changed=0. IDEMPOTENT.
  RUN B   state 1: none pre-exist, gate fails
          -> plan remove/remove/remove; Restore skipped; Remove changed x3;
             all three ABSENT afterwards; play fails with the reworded message.
  RUN C   state 2: all three pre-exist with DIFFERENT content, gate fails
          -> plan restore x3; all three md5s back to their PRE values.
  RUN D   state 3: content already CORRECT, only owner drifted
          (chown developer:developer), gate fails    <-- round-3 blocker repro
          -> plan restore x3; Restore reported ok (byte-identical no-op);
             Remove skipped x3; ALL THREE FILES SURVIVE with unchanged md5
             (58500a27…, ec0c36c9…, 9c1fcdb0…), ownership normalised to
             root:root 0644. The old role deleted both files here.
  RUN E   state 4 + state 2 mixed: two converged, 05-forge.conf hand-edited
          -> plan leave/leave/restore; snapshot taken only for 05-forge.conf;
             Restore changed only 05-forge.conf; nothing removed; POST == PRE.
  RUN E2  state 4 with the two `leave` snapshots POISONED
          (192.168.50.99 POISONED-STALE.bi-services.be)
          -> Restore skipped for both; `grep -c POISONED` on the live files
             returns 0. A stale snapshot can never reach a converged file.
  RUN F   state 5: rollback.yml included with forge_dns_rollback_plan undefined
          -> every loop skipped, POST == PRE, nothing touched.
  RUN G   bad file removed, real convergence: 3 changed, play OK, and the
          IaC harness answers A+AAAA correctly for every name after the role's
          own FTL re-exec (no container restart), PTR .194 = alertmanager.
  RUN G2  immediate re-run after that real content change: changed=0.
