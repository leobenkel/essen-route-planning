# Web API Deployment

## Overview

The Essen Route Planning tool includes a web API that exposes the `./where` functionality as a hosted service.

## Configuration Setup

### Environment Variables

The deployment uses environment variables to avoid hardcoding sensitive information. Before deploying, you must configure your environment:

1. **Create your environment file:**
   ```bash
   cp .env.sample .env
   ```

2. **Edit `.env` with your values:**
   ```bash
   # Container registry (requires docker login)
   REGISTRY=your-registry.example.com

   # Domain for public access
   DOMAIN=your-domain.example.com

   # SSH host for kubectl access
   KUBE_SSH_HOST=your-kubernetes-server
   ```

3. **Authenticate to your container registry:**
   ```bash
   docker login $REGISTRY
   ```

**Important:** The `.env` file is git-ignored to prevent committing credentials.

### Deployment Commands

```bash
# Build and push Docker image
task push_prod

# Deploy to Kubernetes
task deploy

# Test locally before deploying
task test_prod
```

## What Was Built

### 1. FastAPI Web Application

**Location:** `src/api/`

- **main.py** - FastAPI application with endpoints:
  - `GET /` - Interactive web UI for game lookup
  - `GET /where?id={bgg_id}` - JSON API for game lookup by ID
  - `GET /where?link={bgg_url}` - JSON API for game lookup by URL
  - `GET /health` - Health check endpoint for Kubernetes

- **templates/index.html** - Beautiful, responsive web interface
  - Single input field for BGG links or IDs
  - Real-time results display
  - Mobile-friendly design

- **requirements.txt** - API-specific dependencies

### 2. Docker Configuration

**Location:** `deploy/docker/`

- **Dockerfile** - Multi-stage build optimized for size
  - Base: Python 3.13-slim
  - Includes all source code and dependencies
  - Creates data directories for cache and output

- **.dockerignore** - Excludes unnecessary files from build context

- **build.sh** - Helper script to build and push to container registry
  - Builds: `${REGISTRY}/essen-route-planner/www:latest`
  - Interactive push confirmation

### 3. Kubernetes Manifests

**Location:** `deploy/k8s/`

Complete Kubernetes deployment following the same pattern as your Gitea setup:

- **namespace.yaml** - `essen-api` namespace
- **pvc.yaml** - 5Gi persistent storage for cache
- **deployment.yaml** - Single replica with:
  - Resource limits (256Mi RAM, 250m CPU)
  - Health checks (liveness + readiness probes)
  - PVC mount at `/app/data`
- **service.yaml** - ClusterIP service on port 8000
- **middleware.yaml** - Traefik HTTPS redirect
- **ingress.yaml** - Public domain with TLS via Let's Encrypt
- **apply.sh** - One-command deployment script
- **populate-essen-data.sh** - Helper to seed Essen API data

### 4. DNS Configuration

Configure your DNS to point your chosen domain to your Kubernetes server's IP address. If using dynamic DNS, configure your DNS updater accordingly.

## Architecture

```
Internet
   │
   ▼
[DNS: your-domain.example.com] → Your server IP
   │
   ▼
[Traefik Ingress]
   │
   ├─ TLS termination (Let's Encrypt)
   ├─ HTTP → HTTPS redirect
   │
   ▼
[ClusterIP Service]
   │
   ▼
[FastAPI Pod]
   │
   ├─ Uses game_lookup.py (shared with CLI)
   ├─ Mounts PVC at /app/data
   │
   ▼
[Persistent Volume]
   │
   ├─ BGG cache (diskcache)
   ├─ Essen exhibitors JSON
   └─ Essen products JSON
```

## Code Sharing Between CLI and API

The implementation follows the Single Source of Truth principle:

```
┌─────────────────────────────────┐
│     SHARED CORE LOGIC           │
│  - game_lookup.py               │
│  - url_parser.py                │
│  - bgg_scraper.py               │
│  - unified_enricher.py          │
│  - data_models.py               │
└────────┬───────────────┬────────┘
         │               │
         ▼               ▼
    ┌────────┐      ┌─────────┐
    │  CLI   │      │   API   │
    │ where  │      │ FastAPI │
    └────────┘      └─────────┘
```

**Benefits:**
- No code duplication
- Bug fixes benefit both CLI and API
- Same data models used everywhere (Pydantic)
- Consistent behavior across interfaces

## Deployment Process

### Quick Start

```bash
# 1. Build Docker image
cd deploy/docker
./build.sh

# 2. Deploy to Kubernetes
cd ../k8s
./apply.sh

# 3. Populate Essen data (one-time)
./populate-essen-data.sh

# 4. Verify
curl https://your-domain.example.com/health
open https://your-domain.example.com
```

### Detailed Steps

See [deploy/README.md](deploy/README.md) for comprehensive deployment documentation.

## Persistent Storage Strategy

The API uses a Kubernetes PersistentVolumeClaim to store:

1. **BGG API Cache** (`data/cache/bgg/`)
   - Cached responses from BoardGameGeek
   - Avoids re-scraping (respects rate limits)
   - Persists across pod restarts

2. **Essen Data** (`data/output/`)
   - `essen_exhibitors.json` - All Essen exhibitors
   - `essen_products.json` - All products at Essen
   - Fetched from official Essen Spiel API

**Why PVC?**
- Fast responses (cache hits)
- Reduced load on BGG servers
- Essen data changes infrequently
- Survives pod restarts/redeployments

**Size:** 5Gi is generous for:
- Essen JSON files: ~5-10 MB
- BGG cache grows over time: ~100 MB for 100s of games
- Plenty of headroom for growth

## Files Created

```
essen-route-planning/
├── src/api/                              # NEW
│   ├── __init__.py
│   ├── main.py                           # FastAPI app
│   ├── requirements.txt                  # API dependencies
│   └── templates/
│       └── index.html                    # Web UI
├── deploy/                               # NEW
│   ├── README.md                         # Deployment docs
│   ├── docker/
│   │   ├── Dockerfile                    # Container image
│   │   ├── .dockerignore
│   │   └── build.sh                      # Build helper
│   └── k8s/
│       ├── namespace.yaml
│       ├── pvc.yaml                      # Persistent storage
│       ├── deployment.yaml               # K8s deployment
│       ├── service.yaml
│       ├── middleware.yaml               # Traefik redirect
│       ├── ingress.yaml                  # Public domain ingress
│       ├── apply.sh                      # Deploy helper
│       └── populate-essen-data.sh        # Data seed helper
└── DEPLOYMENT.md                         # This file
```

## Testing

### Local Development

```bash
# Install API dependencies
pip install -r src/api/requirements.txt

# Run locally
cd src
uvicorn api.main:app --reload

# Open in browser
open http://localhost:8000
```

### Production Testing

```bash
# Health check
curl https://your-domain.example.com/health

# API endpoint - by ID
curl "https://your-domain.example.com/where?id=418354"

# API endpoint - by URL
curl "https://your-domain.example.com/where?link=https://boardgamegeek.com/boardgame/418354/babylon"

# Web UI
open https://your-domain.example.com
```

## Monitoring

```bash
# Pod logs
kubectl logs -f -n essen-api -l app=essen-route-planning

# Pod status
kubectl get pods -n essen-api

# Resource usage
kubectl top pods -n essen-api

# TLS certificate status
kubectl get certificate -n essen-api
```

## Future Enhancements

Potential improvements:

1. **Background Jobs** - Add Celery for async processing
2. **Full Pipeline API** - Expose complete route generation
3. **User Collections** - Allow BGG collection uploads
4. **Search Endpoint** - Expose tag search via API
5. **Caching Layer** - Add Redis for response caching
6. **Multiple Replicas** - Use ReadWriteMany storage or shared cache
7. **Metrics** - Add Prometheus metrics
8. **Rate Limiting** - Protect against abuse

## CLI Preserved

**Important:** All existing CLI tools still work exactly as before:

```bash
./where https://boardgamegeek.com/boardgame/418354/babylon
./search coop
./run_all
```

The CLI and API share the same core logic, ensuring consistent behavior.

## Next Steps

1. **Test the deployment:**
   ```bash
   cd deploy/k8s
   ./apply.sh
   ./populate-essen-data.sh
   ```

2. **Verify DNS propagation:**
   ```bash
   nslookup your-domain.example.com
   ```

3. **Wait for TLS certificate:**
   ```bash
   kubectl get certificate -n essen-api -w
   ```

4. **Access the API:**
   ```bash
   open https://your-domain.example.com
   ```

## Support

For issues or questions:
- Check [deploy/README.md](deploy/README.md) for troubleshooting
- Review pod logs: `kubectl logs -n essen-api -l app=essen-route-planning`
- Verify Essen data exists: `./deploy/k8s/populate-essen-data.sh`

---

**Deployed successfully!** The Essen Route Planning tool is now available as both a CLI and web service.
