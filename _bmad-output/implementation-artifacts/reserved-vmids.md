# Reserved VMIDs (homelab cluster)

This doc prevents VMID collisions between manually-created CTs/VMs and Terraform-auto-numbered resources. Update whenever a VMID is claimed, even outside Terraform state.

## Currently reserved

| VMID | Node | Name | Type | Managed by | Notes |
|------|------|------|------|------------|-------|
| 100 | pve1 | smarthome | VM | manual | Zigbee USB pinned |
| 101 | pve1 | ct-docker-01 | LXC | Terraform | |
| 102 | pve1 | ct-media-01 | LXC | Terraform | mounts shared-nfs-bulk |
| 103 | pve1 | vm-haos-01 | VM | Terraform | Home Assistant OS |
| 104 | pve1 | ct-zeroclaw-01 | LXC | manual | |
| 105 | pve2 | ct-pbs-migration | LXC | manual (Story 1.2) | **TEMPORARY** — migration-window PBS, remove per runbook |
| 150 | pve1 | ct-dev-homelab | LXC | Terraform | operator workbench |
| 151 | pve2 | ct-sparkle-cps | LXC | manual | CPS-Fabric project |
| 152 | pve2 | ct-dev-test | LXC | Terraform | disposable test target |
| 153 | pve2 | ct-isabelle | LXC | Terraform | Isabelle project |
| 160 | pve3 | ct-ai-01 | LXC | manual | iGPU pinned (Ollama) |
| 162 | pve3 | ct-quant-trading | LXC | Terraform | HA-critical |
| 999 | pve1 | ubuntu-dev-template | VM | template | |
| 9000 | pve1 | ubuntu-22.04-cloudimg | VM | template | |

## Transient / planned

| VMID | Purpose | Expected duration |
|------|---------|-------------------|
| 250 | CT150 workbench replica on pve3 during Epic 4 (Story 4.3) | ~1 week (Epic 5 window) |

## Rules

1. Before creating a new CT/VM (manual or Terraform), check this table.
2. Before running `terraform apply` with new CT resources, `terraform state list` to verify the auto-numbered VMID doesn't collide.
3. After creating a manual (non-Terraform) CT/VM, add it here in the same commit where its storage.cfg/PVE config first appears.
4. When retiring a VMID, move its row to a "Retired" section with retirement date — don't delete, since the number takes 24 h to fully clear from cluster state.
