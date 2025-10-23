# Local Development Guide

Multiple ways to run the Essen Route Planning API locally for development and testing.

## Quick Start (Recommended)

### Option 1: Docker Compose (Easiest)

One command to rule them all:

```bash
./dev.sh
```

This will:
1. Check if Essen data exists (offer to fetch if missing)
2. Build the Docker image
3. Start the API with live reload
4. Mount your local code (changes are reflected immediately)

Access the UI at: **http://localhost:8000**

To stop:
```bash
# Press Ctrl+C, then:
docker-compose down
```

#### Manual docker-compose commands:

```bash
# Start in foreground (see logs)
docker-compose up --build

# Start in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild image
docker-compose build --no-cache
```

### Option 2: Local Python (No Docker)

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r src/api/requirements.txt

# 3. Fetch Essen data (one-time)
./scripts/step_03

# 4. Run the API
cd src
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Access the UI at: **http://localhost:8000**

### Option 3: Dev Dockerfile

For testing the Docker build without docker-compose:

```bash
# Build dev image
docker build -f deploy/docker/Dockerfile.dev -t essen-api-dev .

# Run with volume mounts
docker run -p 8000:8000 \
  -v $(pwd)/src:/app/src:ro \
  -v $(pwd)/data:/app/data \
  essen-api-dev
```

Access the UI at: **http://localhost:8000**

## Testing the API

Once running, try these:

### Web UI
```bash
# Open in browser
open http://localhost:8000
```

### REST API
```bash
# Health check
curl http://localhost:8000/health

# Look up by game ID
curl "http://localhost:8000/where?id=418354" | jq

# Look up by BGG URL
curl "http://localhost:8000/where?link=https://boardgamegeek.com/boardgame/418354/babylon" | jq
```

### Interactive API docs (FastAPI)
```bash
# Swagger UI
open http://localhost:8000/docs

# ReDoc
open http://localhost:8000/redoc
```

## Development Workflow

### With Docker Compose (Live Reload)

The docker-compose setup mounts your source code, so changes are reflected immediately:

1. **Start the service:**
   ```bash
   ./dev.sh
   # or: docker-compose up
   ```

2. **Edit code:**
   - Make changes to `src/api/main.py`, templates, etc.
   - Uvicorn will automatically reload
   - Refresh browser to see changes

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop:**
   ```bash
   docker-compose down
   ```

### With Local Python (Live Reload)

1. **Start with reload:**
   ```bash
   cd src
   uvicorn api.main:app --reload
   ```

2. **Edit code:**
   - Make changes to any Python file
   - Uvicorn auto-reloads on file changes

3. **Stop:**
   - Press `Ctrl+C`

## Populating Essen Data

The API needs Essen exhibitor and product data. If missing, you'll see "Essen data not available" errors.

### Fetch Data Locally

```bash
# Make sure you're in the project root
./scripts/step_03
```

This fetches:
- `data/output/essen_exhibitors.json`
- `data/output/essen_products.json`

The data is cached and persists across restarts.

### Using with Docker Compose

The docker-compose setup mounts `./data` directory, so data fetched locally is automatically available in the container.

## Troubleshooting

### "Essen data not available"

**Solution:** Fetch the data first:
```bash
./scripts/step_03
```

### "Port 8000 already in use"

**Solution:** Stop other services or change the port:

```bash
# In docker-compose.yml, change:
ports:
  - "8001:8000"  # Use port 8001 instead

# Or stop the conflicting service
lsof -ti:8000 | xargs kill
```

### "Module not found" errors

**Solution:** Make sure you're in the right directory:

```bash
# For local Python, run from src/
cd src
uvicorn api.main:app --reload

# For Docker, run from project root
docker-compose up
```

### Changes not reflecting

**Docker Compose:**
- Rebuild the image: `docker-compose up --build`
- Check volume mounts are correct in `docker-compose.yml`

**Local Python:**
- Make sure `--reload` flag is enabled
- Check you saved the file

### Container crashes immediately

**Check logs:**
```bash
docker-compose logs
```

**Common causes:**
- Missing dependencies: Rebuild with `docker-compose build --no-cache`
- Port conflict: Change port in docker-compose.yml
- Syntax errors: Check Python code

## File Structure

```
essen-route-planning/
├── src/api/
│   ├── main.py              # FastAPI app (edit this!)
│   ├── templates/
│   │   └── index.html       # Web UI (edit this!)
│   └── requirements.txt     # API dependencies
├── data/
│   ├── cache/               # BGG cache (auto-populated)
│   └── output/              # Essen data (fetch with step_03)
├── docker-compose.yml       # Docker Compose config
├── deploy/docker/
│   ├── Dockerfile           # Production Dockerfile
│   └── Dockerfile.dev       # Development Dockerfile
└── dev.sh                   # Quick start script
```

## Hot Reload Details

### What triggers reload?

**Python files:**
- Changes to `src/api/*.py`
- Changes to any imported modules
- Uvicorn detects changes and restarts

**Templates:**
- Changes to `src/api/templates/*.html`
- Jinja2 auto-reloads templates in debug mode
- Just refresh browser (no need to restart)

**Dependencies:**
- Changes to `requirements.txt` require rebuild
- Run `docker-compose up --build` or reinstall with pip

### What doesn't trigger reload?

- `.dockerignore` changes (rebuild needed)
- `Dockerfile` changes (rebuild needed)
- `docker-compose.yml` changes (restart needed)

## Environment Variables

You can customize behavior with environment variables:

```bash
# In docker-compose.yml:
environment:
  - PYTHONUNBUFFERED=1
  - LOG_LEVEL=debug        # Add custom vars
  - BGG_CACHE_TTL=3600
```

```bash
# Or on command line:
docker-compose run -e LOG_LEVEL=debug essen-api
```

## Next Steps

1. **Start developing:**
   ```bash
   ./dev.sh
   ```

2. **Make changes** to `src/api/main.py` or templates

3. **Test in browser:** http://localhost:8000

4. **When ready to deploy:**
   - See [deploy/README.md](deploy/README.md)
   - Build production image: `cd deploy/docker && ./build.sh`
   - Deploy to Kubernetes: `cd deploy/k8s && ./apply.sh`

## Tips

- Use FastAPI's **auto-generated docs** at http://localhost:8000/docs for API testing
- Check **logs** frequently: `docker-compose logs -f`
- **jq** is useful for pretty-printing JSON API responses
- Use **browser DevTools** to debug the web UI
- VSCode's **REST Client** extension is great for API testing

Happy coding! 🎉
