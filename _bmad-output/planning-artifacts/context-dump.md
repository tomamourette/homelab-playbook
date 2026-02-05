# Product Brief: Homelab Infrastructure

## 1. Product Vision

### Core Problem
The current "brownfield" homelab infrastructure lacks correct, up-to-date documentation and a structured management process. Services exist (Proxmox, Docker) but their configuration and operational status are not consistently maintained or monitored. A previous plan exists but was never finished or updated.

### Target Audience
Larry (Primary User/Administrator).

### Success Criteria
- **Correct Documentation:** Accurate, up-to-date documentation for all infrastructure and services.
- **Operational Stability:** All services up, running, and correctly configured.
- **Process:** A stable, ongoing BMAD-based management process to finish the original plan.
- **Observability:** Comprehensive monitoring and a central dashboard for all services.

### Excitement Factors
- Regaining control and stability over the infrastructure.
- Establishing a reliable, structured process for future growth.

## 2. Context & Scope

### Existing Infrastructure ("Brownfield")
- **Repo 1: `homelab-infra`**
  - Technology: Terraform & Ansible
  - Target: Proxmox VE
  - Scope: Infrastructure provisioning (VMs, LXCs, networking)
- **Repo 2: `homelab-apps`**
  - Technology: Docker Compose
  - Target: Application layer (running on the infra)
  - Key Apps: Traefik (ingress), etc.

### Goal
Bring these existing brownfield components under the management of this new `homelab-playbook` using the BMAD method.
