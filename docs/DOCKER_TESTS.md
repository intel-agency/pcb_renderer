# Platform Smoke Tests

This directory contains platform smoke tests to validate the PCB Renderer application across different operating systems and container environments.

## Test Files

| File | Description |
|------|-------------|
| `Dockerfile.test.linux` | Alpine Linux-based smoke test (lightweight) |
| `Dockerfile.test.debian` | Debian/Ubuntu-based smoke test (mainstream distro) |
| `Dockerfile.test.windows` | Windows Server Core-based smoke test |
| `docker-compose.test.yml` | Docker Compose configuration for running all tests |
| `.dockerignore` | Files excluded from Docker build context |

## Running Smoke Tests Locally

### Individual Platform Tests

**Linux (Alpine):**
```bash
docker build -t pcb-renderer-test:linux-alpine -f Dockerfile.test.linux .
docker run --rm pcb-renderer-test:linux-alpine
```

**Linux (Debian/Ubuntu):**
```bash
docker build -t pcb-renderer-test:linux-debian -f Dockerfile.test.debian .
docker run --rm pcb-renderer-test:linux-debian
```

**Windows:**
```powershell
# Requires Docker Desktop with Windows containers enabled
docker build -t pcb-renderer-test:windows -f Dockerfile.test.windows .
docker run --rm pcb-renderer-test:windows
```

### Using Docker Compose

**Run all Linux tests:**
```bash
docker-compose -f docker-compose.test.yml up test-linux-alpine test-linux-debian
```

**Run specific test:**
```bash
docker-compose -f docker-compose.test.yml up test-linux-alpine
```

**Run Windows test:**
```powershell
# Requires Docker Desktop with Windows containers mode
docker-compose -f docker-compose.test.yml up test-windows
```

## What Gets Tested

Each smoke test validates:

1. **Basic render** - Renders `board_alpha.json` to SVG
2. **PNG export** - Tests format conversion to PNG
3. **Validation errors** - Tests `--permissive` mode with invalid board
4. **Export JSON** - Tests `--export-json` feature
5. **Full test suite** - Runs `pytest --cov` with all tests

## CI Integration

The platform smoke tests run automatically on GitHub Actions:

- **Alpine Linux test** - Runs in Docker on `ubuntu-latest`
- **Debian/Ubuntu test** - Runs in Docker on `ubuntu-latest`  
- **Windows test** - Runs in Docker on `windows-2022`
- **macOS test** - Runs natively on `macos-latest` (no Docker)

See `.github/workflows/docker-smoke-tests.yml` for CI configuration.

## Platform Notes

### Linux (Alpine)
- Minimal base image (~50MB)
- Uses `apk` package manager
- Best for production deployments

### Linux (Debian/Ubuntu)
- Mainstream distro compatibility
- Uses `apt` package manager
- Better for development/compatibility testing

### Windows
- Requires Windows Server Core base image (~4GB)
- Requires Docker Desktop with Windows containers mode
- Only runs on Windows runners in CI

### macOS
- Docker doesn't support native macOS containers
- macOS smoke tests run natively on `macos-latest` runner (not in Docker)
- Uses the same test sequence as Docker tests but runs directly on the host
- See `.github/workflows/docker-smoke-tests.yml` job `macos-native`

## Troubleshooting

**Build fails on Windows:**
- Ensure Docker Desktop is in Windows containers mode (not Linux containers)
- Check that Python download URL is accessible

**Tests fail inside container:**
- Check that all required files are copied (see Dockerfile COPY commands)
- Verify `.dockerignore` isn't excluding needed files

**Slow build times:**
- Use Docker BuildKit: `DOCKER_BUILDKIT=1 docker build ...`
- Consider layer caching for faster rebuilds
