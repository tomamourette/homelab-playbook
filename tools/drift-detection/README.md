# Drift Detection Tool - SSH & Docker Inspection

This tool connects to remote Docker hosts via SSH and extracts container configurations for drift analysis. It enables operators to compare the runtime state of containers against their git-tracked desired state.

## Features

- **SSH Connection Management**: Secure connections to target hosts using SSH keys
- **Docker Inspection**: Extract detailed container configurations via Docker SDK
- **Git Baseline Loading**: Load baseline configurations from git repositories for drift comparison
- **Docker Compose Parsing**: Parse and merge Docker Compose files with endpoint-specific overrides
- **Environment Variable Substitution**: Handle .env files and variable substitution in compose files
- **Structured Data Extraction**: Captures labels, networks, volumes, environment variables, and more
- **Multi-Host Support**: Inspect containers across multiple hosts in a single run
- **Error Handling**: Graceful handling of connection and inspection failures
- **Flexible Configuration**: Environment-based configuration with .env support

## Architecture

```
┌─────────────┐         SSH         ┌──────────────────┐
│   dev-vm    │ ───────────────────> │  ct-docker-01    │
│             │                      │  (192.168.50.19) │
│ Python      │         SSH         └──────────────────┘
│ Drift Tool  │ ───────────────────>
│             │                      ┌──────────────────┐
└─────────────┘                      │  ct-media-01     │
                                     │  (192.168.50.161)│
                                     └──────────────────┘
```

The tool runs on dev-vm and uses SSH to connect to target Docker hosts. It leverages the Docker Python SDK to communicate with the Docker daemon over the SSH tunnel.

## Prerequisites

- Python 3.8 or higher
- SSH access to target Docker hosts
- SSH key authentication configured
- Docker running on target hosts

## Installation

1. **Clone the repository** (if not already done):
   ```bash
   cd homelab-playbook/tools/drift-detection/
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.sample .env
   # Edit .env with your settings
   ```

## Configuration

Create a `.env` file based on `.env.sample`:

```bash
# SSH Configuration
SSH_KEY_PATH=~/.ssh/id_rsa

# Target Hosts (comma-separated)
TARGET_HOSTS=192.168.50.19,192.168.50.161

# SSH Username
SSH_USERNAME=root

# SSH Connection Timeout (seconds)
SSH_TIMEOUT=10

# Docker Connection Timeout (seconds)
DOCKER_TIMEOUT=30

# Output Settings
OUTPUT_FORMAT=json
OUTPUT_DIR=./output

# Logging Level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

### SSH Key Setup

Ensure your SSH key is configured for passwordless authentication:

```bash
# Copy your public key to target hosts (if not already done)
ssh-copy-id -i ~/.ssh/id_rsa root@192.168.50.19
ssh-copy-id -i ~/.ssh/id_rsa root@192.168.50.161

# Test connection
ssh root@192.168.50.19 "docker ps"
```

## Usage

### Basic Usage

Inspect containers on configured hosts:

```python
from config import load_config
from docker_inspector import inspect_multiple_hosts
import json

# Load configuration from .env
config = load_config()

# Inspect all configured hosts
results = inspect_multiple_hosts(
    hosts=config.target_hosts,
    username=config.ssh_username,
    ssh_key_path=config.ssh_key_path
)

# Print results
print(json.dumps(results, indent=2))
```

### Single Host Inspection

```python
from docker_inspector import inspect_host

result = inspect_host(
    host="192.168.50.19",
    username="root",
    ssh_key_path="~/.ssh/id_rsa"
)

print(f"Found {result['container_count']} containers")
for container in result['containers']:
    print(f"  - {container['name']}: {container['status']}")
```

### Using Context Manager

For more control over the inspection process:

```python
from docker_inspector import DockerInspector

with DockerInspector(
    host="192.168.50.19",
    username="root",
    ssh_key_path="~/.ssh/id_rsa"
) as inspector:
    # List containers
    container_ids = inspector.list_containers()
    
    # Inspect specific container
    for cid in container_ids:
        info = inspector.inspect_container(cid)
        print(f"{info.name}: {info.image}")
```

### Example Script

Run the provided example script:

```bash
python example_usage.py
```

Edit `example_usage.py` and uncomment the examples you want to run.

## Git Baseline Loading

The git baseline loader reads Docker Compose configurations from your git repositories (homelab-apps and homelab-infra) to establish the desired state for comparison against running containers.

### Basic Baseline Loading

Load all baseline configurations from homelab-apps:

```python
from git_config_loader import GitConfigLoader

loader = GitConfigLoader(
    homelab_apps_path="../../../homelab-apps"
)

baselines = loader.load_all_baselines()

for baseline in baselines:
    print(f"{baseline.stack_name}/{baseline.name}: {baseline.image}")
```

### Loading with Endpoint-Specific Overrides

If you have endpoint-specific compose files (e.g., `docker-compose.ct-docker-01.yml`):

```python
loader = GitConfigLoader(
    homelab_apps_path="../../../homelab-apps",
    homelab_infra_path="../../../homelab-infra",
    endpoint="ct-docker-01"  # Load ct-docker-01 overrides
)

baselines = loader.load_all_baselines()
```

The loader will:
1. Load base `docker-compose.yml`
2. Find and merge `docker-compose.ct-docker-01.yml` if it exists
3. Load `.env` or `.env.sample` for variable substitution
4. Substitute all `${VAR}` references in the compose file

### Finding Specific Services

```python
# Find baseline for a specific service
pihole_baseline = loader.get_baseline_by_name("pihole")

if pihole_baseline:
    print(f"Image: {pihole_baseline.image}")
    print(f"Labels: {pihole_baseline.labels}")
    print(f"Networks: {pihole_baseline.networks}")
```

### Using the Convenience Function

For simple use cases:

```python
from git_config_loader import load_git_baselines

result = load_git_baselines(
    homelab_apps_path="../../../homelab-apps",
    endpoint="ct-docker-01"
)

print(f"Loaded {result['count']} baselines")
print(f"Services: {[b['name'] for b in result['baselines']]}")
```

### Stack Discovery

Discover all available stacks:

```python
loader = GitConfigLoader(
    homelab_apps_path="../../../homelab-apps",
    homelab_infra_path="../../../homelab-infra"
)

stacks = loader.discover_stacks()
print(f"Found {len(stacks)} stacks: {[s.name for s in stacks]}")
```

### Running Examples

Try the git loader examples:

```bash
python example_git_loader.py
```

### Baseline Data Structure

Git baselines use a structure similar to `ContainerInfo` for easy comparison:

```json
{
  "name": "pihole",
  "image": "pihole/pihole:2024.01.0",
  "labels": {
    "traefik.enable": "true",
    "traefik.http.routers.pihole-secure.rule": "Host(`pihole.example.com`)"
  },
  "networks": ["proxy", "dns"],
  "volumes": [
    "/opt/pihole/config:/etc/pihole:rw",
    "./config/custom.list:/etc/pihole/custom.list:ro"
  ],
  "environment": {
    "TZ": "America/New_York",
    "WEBPASSWORD": "admin123"
  },
  "ports": [
    "192.168.50.19:53:53/tcp",
    "8053:80/tcp"
  ],
  "stack_name": "dns-pihole",
  "compose_file": "/path/to/dns-pihole/docker-compose.yml"
}
```

## Data Structure

The tool extracts the following container information:

```json
{
  "container_id": "abc123...",
  "name": "my-container",
  "image": "nginx:latest",
  "status": "running",
  "labels": {
    "com.docker.compose.project": "myapp",
    "com.docker.compose.service": "web"
  },
  "networks": {
    "bridge": {
      "IPAddress": "172.17.0.2",
      "Gateway": "172.17.0.1"
    }
  },
  "volumes": [
    {
      "type": "bind",
      "source": "/host/path",
      "destination": "/container/path",
      "mode": "rw",
      "rw": true
    }
  ],
  "environment": {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "MY_VAR": "value"
  },
  "ports": {
    "80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]
  },
  "created": "2024-01-01T12:00:00.000000000Z",
  "started": "2024-01-01T12:00:05.000000000Z"
}
```

## Error Handling

The tool defines specific exceptions for different failure modes:

- **SSHConnectionError**: SSH connection failures (auth, network, timeout)
- **DockerConnectionError**: Docker daemon connection issues
- **ContainerInspectionError**: Container inspection failures

All exceptions include descriptive error messages for troubleshooting.

Example:

```python
from docker_inspector import (
    inspect_host,
    SSHConnectionError,
    DockerConnectionError,
    ContainerInspectionError
)

try:
    result = inspect_host("192.168.50.19", "root")
except SSHConnectionError as e:
    print(f"SSH failed: {e}")
except DockerConnectionError as e:
    print(f"Docker connection failed: {e}")
except ContainerInspectionError as e:
    print(f"Inspection failed: {e}")
```

## Development

### Code Style

This project follows PEP 8 and uses type hints throughout:

```bash
# Check code style
flake8 docker_inspector.py config.py

# Type checking
mypy docker_inspector.py config.py
```

### Running Tests

(Future: Unit tests will be added in Story 1.2)

```bash
pytest tests/
```

## Troubleshooting

### SSH Connection Issues

**Problem**: `Authentication failed for root@192.168.50.19`

**Solution**: Ensure SSH key is added to target host:
```bash
ssh-copy-id -i ~/.ssh/id_rsa root@192.168.50.19
```

**Problem**: `Connection timed out`

**Solution**: Check network connectivity and firewall rules:
```bash
ping 192.168.50.19
telnet 192.168.50.19 22
```

### Docker Connection Issues

**Problem**: `Failed to connect to Docker on 192.168.50.19`

**Solution**: Verify Docker is running on target host:
```bash
ssh root@192.168.50.19 "systemctl status docker"
```

**Problem**: `Permission denied accessing Docker socket`

**Solution**: Ensure SSH user has Docker permissions:
```bash
ssh root@192.168.50.19 "usermod -aG docker $USER"
```

## Project Structure

```
drift-detection/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.sample              # Environment configuration template
├── .env                     # Your configuration (git-ignored)
├── __init__.py              # Package initialization
├── config.py                # Configuration management
├── docker_inspector.py      # Docker inspection module (Story 1.1)
├── git_config_loader.py     # Git baseline loader (Story 1.2)
├── example_usage.py         # Docker inspection examples
├── example_git_loader.py    # Git loader examples
└── output/                  # Output directory (created automatically)
    ├── container_inspection.json
    └── git_baselines.json
```

## Roadmap

- **Story 1.1**: SSH Connection & Docker Inspection ✅
- **Story 1.2**: Git Repository Baseline Loader ✅
- **Story 1.3** (Next): Drift Comparison Engine (compare runtime vs git baselines)
- **Story 1.4**: Reporting & Notifications
- **Story 1.5**: CI/CD Integration

## Contributing

This is part of the homelab-playbook project. Follow the standard git workflow:

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -am "Add feature"`
3. Push to origin: `git push origin feature/your-feature`
4. Open a pull request

## License

Part of the homelab-playbook project.

## Story Context

### Story 1.1: SSH Connection & Docker Inspection Setup ✅

**Acceptance Criteria:**
- ✅ Dev-vm has SSH access to ct-docker-01 (192.168.50.19) and ct-media-01 (192.168.50.161)
- ✅ Drift detector connects to target hosts successfully
- ✅ Authenticates via SSH key
- ✅ Uses Docker SDK to list all running containers
- ✅ Extracts container inspect data (labels, networks, volumes, environment)
- ✅ Handles connection failures gracefully with clear error messages

All acceptance criteria met.

### Story 1.2: Git Repository Baseline Loader ✅

**Acceptance Criteria:**
- ✅ homelab-apps and homelab-infra repos are cloned locally
- ✅ Drift detector loads git baselines successfully
- ✅ Parses all Docker Compose files in `homelab-apps/stacks/*/`
- ✅ Handles endpoint-specific overrides (`docker-compose.<endpoint>.yml`)
- ✅ Extracts compose configurations (services, labels, networks, volumes)
- ✅ Stores normalized config data for comparison

**Implementation:**
- `git_config_loader.py` with GitConfigLoader class
- Parses Docker Compose YAML files
- Merges base + endpoint-specific compose files
- Handles `.env` variable substitution
- Returns structured data matching docker_inspector.py format
- Comprehensive error handling and logging

All acceptance criteria met.
