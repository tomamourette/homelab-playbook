# Drift Detection Tool - SSH & Docker Inspection

This tool connects to remote Docker hosts via SSH and extracts container configurations for drift analysis. It enables operators to compare the runtime state of containers against their git-tracked desired state.

## Features

- **SSH Connection Management**: Secure connections to target hosts using SSH keys
- **Docker Inspection**: Extract detailed container configurations via Docker SDK
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
├── config.py                # Configuration management
├── docker_inspector.py      # Main inspection module
├── example_usage.py         # Usage examples
└── output/                  # Output directory (created automatically)
    └── container_inspection.json
```

## Roadmap

- **Story 1.1** (Current): SSH Connection & Docker Inspection ✅
- **Story 1.2** (Next): Comparison Engine (compare runtime vs git)
- **Story 1.3**: Reporting & Notifications
- **Story 1.4**: CI/CD Integration

## Contributing

This is part of the homelab-playbook project. Follow the standard git workflow:

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -am "Add feature"`
3. Push to origin: `git push origin feature/your-feature`
4. Open a pull request

## License

Part of the homelab-playbook project.

## Story Context

**Story 1.1: SSH Connection & Docker Inspection Setup**

**Acceptance Criteria:**
- ✅ Dev-vm has SSH access to ct-docker-01 (192.168.50.19) and ct-media-01 (192.168.50.161)
- ✅ Drift detector connects to target hosts successfully
- ✅ Authenticates via SSH key
- ✅ Uses Docker SDK to list all running containers
- ✅ Extracts container inspect data (labels, networks, volumes, environment)
- ✅ Handles connection failures gracefully with clear error messages

All acceptance criteria are met by this implementation.
