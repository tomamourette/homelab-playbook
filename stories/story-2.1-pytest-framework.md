# Story 2.1: pytest Test Framework Setup

**Epic:** Epic 2: Media Pipeline Validation & Automated Fixes
**Story:** 2.1 (Framework Setup)

## Goal

Establish a robust `pytest` test harness that allows us to run integration tests against the homelab media stack. This foundation will be used by all subsequent stories in Epic 2 (Stories 2.2 through 2.10).

## Acceptance Criteria

1.  **Directory Structure:** A `tests/pipeline/` directory exists in `homelab-playbook`.
2.  **Dependencies:** `tests/pipeline/requirements.txt` is created containing necessary libraries (`pytest`, `requests`, `python-dotenv`).
3.  **Configuration Loading:** The framework can load environment variables (API keys, URLs) from a local `.env` file (which is git-ignored).
4.  **API Client Fixtures:** `tests/pipeline/conftest.py` implements reusable Pytest fixtures for connecting to:
    *   Overseerr
    *   Radarr
    *   Sonarr
    *   Prowlarr
    *   qBittorrent
    *   Plex
5.  **Fixture Logic:** Each fixture should return a configured `requests.Session` (or custom client object) pre-loaded with the correct Base URL and API Key headers.
6.  **Dummy Test:** A simple `test_framework_sanity.py` confirms that fixtures load correctly (no actual API calls needed for this specific sanity check, just verifying the harness works).
7.  **Execution:** Running `pytest tests/pipeline/ -v` executes successfully.

## Technical Approach

### 1. File Structure
Create the following files:

```text
homelab-playbook/
└── tests/
    └── pipeline/
        ├── .env.sample             # Template for secrets
        ├── .gitignore              # Ignore .env and __pycache__
        ├── conftest.py             # Fixture definitions
        ├── requirements.txt        # Dependencies
        ├── utils/
        │   └── api_client.py       # Helper class for REST calls
        └── test_framework_sanity.py # Verification test
```

### 2. `conftest.py` Design
Use `pytest.fixture(scope="session")` to load config once.
Create fixtures like `overseerr_client`, `radarr_client`, etc.
Each fixture reads from `os.environ` (loaded via `python-dotenv`).

**Example Fixture:**
```python
@pytest.fixture
def radarr_client(config):
    return MediaClient(
        base_url=config["RADARR_URL"],
        api_key=config["RADARR_API_KEY"]
    )
```

### 3. `api_client.py` Helper
A simple wrapper around `requests` that handles:
*   URL joining
*   Default headers (X-Api-Key)
*   Timeout settings
*   JSON parsing

### 4. Configuration
The `.env` file should map to the architecture:
*   `OVERSEERR_URL=http://192.168.50.19:5055`
*   `RADARR_URL=http://192.168.50.161:7878`
*   etc.

## Dependencies

*   `pytest`
*   `requests`
*   `python-dotenv`

## Definition of Done

*   [ ] `tests/pipeline/` directory created.
*   [ ] `requirements.txt` created and packages installable.
*   [ ] `conftest.py` implements all 6 service fixtures.
*   [ ] `test_framework_sanity.py` passes.
*   [ ] `.env.sample` exists with all required keys.
