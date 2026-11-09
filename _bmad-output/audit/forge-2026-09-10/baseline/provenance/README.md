# Provenance — retained workflow outputs (2026-09-10)

Copies of the 2026-09-09/10 workflow result files that earlier reports cite. Originals lived in
/tmp and were shredded after retention. Before retention every file was scanned by Ansible-vault
VALUE (in-agent, values never printed) and matches replaced with `<REDACTED-VAULT-VALUE>`.

**What matched (key names only):** `vault_smtp_host` (an RFC1918 host IP, 34 occurrences across
co.json and fe2.json — it appears in DNS troubleshooting prose) and `vault_notification_email`
(a notification recipient address, 3 occurrences). Both are *identifiers vaulted for uniformity*,
not credential material. **No credential-shaped vault value (password, token, key, secret)
appeared in any file.** The redaction was therefore conservative, not a leak repair.

Lesson recorded for the audit's own tooling: a by-value scan must classify credential vs
identifier by key name/shape, or it cries wolf on this IP and email in every artefact —
see `tools/vault_scan.py`.
