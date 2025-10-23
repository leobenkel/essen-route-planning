# Deployment Guide

This directory contains everything needed to deploy the Essen Route Planning API to Kubernetes.

## Overview

The API exposes the `./where` functionality as a web service with both a web UI and REST API endpoints.

## Architecture

```
┌─────────────────────────────────────┐
│  User Browser / API Client          │
└──────────────┬──────────────────────┘
               │ HTTPS
               ▼
┌─────────────────────────────────────┐
│  Traefik Ingress (your-domain.com)  │
│  - TLS termination (Let's Encrypt)  │
│  - HTTP → HTTPS redirect            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  essen-api Service (ClusterIP)      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  essen-api Deployment (1 replica)   │
│  - FastAPI application              │
│  - GameLookupService (BGG scraping) │
│  - PVC mounted at /app/data         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Persistent Volume (5Gi)            │
│  - BGG API cache                    │
│  - Essen exhibitor data             │
│  - Essen product listings           │
└─────────────────────────────────────┘
```

## Prerequisites

1. **Kubernetes cluster** with kubectl access
2. **Traefik** ingress controller installed
3. **cert-manager** for automatic TLS certificates
4. **local-path** storage class available
5. **Docker** for building images
6. **Container registry** access (e.g., Docker Hub, GitHub Container Registry, or private registry)
7. **DNS configured** to point to your server IP

## Deployment Steps

### 1. Build and Push Docker Image

```bash
cd deploy/docker
./build.sh

# Or with a specific tag
./build.sh v1.0.0
```

This will:
- Build the Docker image from the project root
- Tag it as `${REGISTRY}/essen-route-planner/www:latest`
- Optionally push to container registry

### 2. Configure DNS

Configure your DNS to point your domain to your Kubernetes server's IP address.

Verify DNS propagation:
```bash
nslookup your-domain.example.com
```

### 3. Deploy to Kubernetes

```bash
cd deploy/k8s
./apply.sh
```

This will create:
- Namespace: `essen-api`
- PersistentVolumeClaim: `essen-api-cache` (5Gi)
- Deployment: `essen-api` (1 replica)
- Service: `essen-api-http` (ClusterIP on port 8000)
- Middleware: `essen-api-redirect-https` (HTTP → HTTPS)
- Ingress: `essen-api-public` (with TLS via Let's Encrypt)

### 4. Verify Deployment

Wait for pod to be ready:
```bash
kubectl get pods -n essen-api -w
```

Check logs:
```bash
kubectl logs -n essen-api -l app=essen-route-planning
```

Wait for TLS certificate:
```bash
kubectl get certificate -n essen-api
```

Test the API:
```bash
# Health check
curl https://your-domain.example.com/health

# Web UI
open https://your-domain.example.com

# API endpoint
curl "https://your-domain.example.com/where?id=418354"
```

## API Endpoints

### Web UI
- **GET /** - Interactive web interface for game lookup

### REST API
- **GET /where?id={bgg_id}** - Look up game by BGG ID
  - Example: `/where?id=418354`

- **GET /where?link={bgg_url}** - Look up game by BGG URL
  - Example: `/where?link=https://boardgamegeek.com/boardgame/418354/babylon`

- **GET /health** - Health check (used by Kubernetes probes)

### Response Format

```json
{
  "game": {
    "object_id": 418354,
    "name": "Babylon",
    "bgg_url": "https://boardgamegeek.com/boardgame/418354/babylon",
    "publishers": ["Ludonova"],
    "average_rating": 7.5,
    "complexity_weight": 2.3,
    "min_players": 2,
    "max_players": 4,
    "playing_time": 60
  },
  "exhibitors": [
    {
      "id": "12345",
      "name": "Ludonova",
      "hall": "3",
      "booth": "3-F123",
      "country": "Germany",
      "website": "https://ludonova.com",
      "match_confidence": 1.0,
      "match_reason": "Publisher 'Ludonova' matched to 'Ludonova' (exact_match, 100%)",
      "product_confirmed": true,
      "product_match_info": "Product 'Babylon' confirmed (95% match)"
    }
  ],
  "matched": true,
  "confirmed_matches": 1
}
```

## Persistent Storage

The API uses a 5Gi PersistentVolumeClaim mounted at `/app/data/` to store:

- **data/cache/bgg/** - Cached BGG API responses (diskcache)
- **data/output/essen_exhibitors.json** - Essen exhibitor data
- **data/output/essen_products.json** - Essen product listings

This ensures:
- Cache persists across pod restarts
- No repeated API calls to BGG (respects rate limits)
- Faster response times for subsequent requests

### Refreshing Cache

To clear the cache and refetch data:

```bash
# Delete the PVC (will be recreated on next deployment)
kubectl delete pvc essen-api-cache -n essen-api

# Restart the deployment
kubectl rollout restart deployment/essen-api -n essen-api
```

## Updating the Deployment

### Update Code

1. Make changes to the code
2. Build new Docker image:
   ```bash
   cd deploy/docker
   ./build.sh v1.0.1
   ```

3. Update deployment image (if using a tag):
   ```bash
   kubectl set image deployment/essen-api -n essen-api \
     essen-api=${REGISTRY}/essen-route-planner/www:v1.0.1
   ```

   Or just trigger a rollout (if using `latest` tag and `imagePullPolicy: Always`):
   ```bash
   kubectl rollout restart deployment/essen-api -n essen-api
   ```

### Scale Deployment

```bash
# Scale up to 2 replicas
kubectl scale deployment/essen-api -n essen-api --replicas=2

# Scale down to 1 replica
kubectl scale deployment/essen-api -n essen-api --replicas=1
```

Note: The current setup uses ReadWriteOnce PVC, so only 1 replica can mount it. For multiple replicas, consider using ReadWriteMany storage or a shared cache service.

## Troubleshooting

### Pod not starting

```bash
# Check pod status
kubectl describe pod -n essen-api -l app=essen-route-planning

# Check logs
kubectl logs -n essen-api -l app=essen-route-planning
```

### TLS certificate not issuing

```bash
# Check certificate status
kubectl get certificate -n essen-api
kubectl describe certificate essen-api-tls -n essen-api

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager
```

### DNS not resolving

```bash
# Check DNS
nslookup your-domain.example.com

# Verify DNS points to your server IP
```

### Essen data not available

The API needs Essen exhibitor and product data. If you see "Essen data not available" errors:

1. SSH into the pod:
   ```bash
   kubectl exec -it -n essen-api deployment/essen-api -- /bin/bash
   ```

2. Manually fetch Essen data (from project root on your local machine):
   ```bash
   python3 src/steps/step3_fetch_essen_data.py
   ```

3. Copy the data to the pod:
   ```bash
   kubectl cp data/output/essen_exhibitors.json essen-api/POD_NAME:/app/data/output/
   kubectl cp data/output/essen_products.json essen-api/POD_NAME:/app/data/output/
   ```

## Monitoring

### View logs
```bash
# Follow logs
kubectl logs -f -n essen-api -l app=essen-route-planning

# Last 100 lines
kubectl logs --tail=100 -n essen-api -l app=essen-route-planning
```

### Check resource usage
```bash
kubectl top pods -n essen-api
```

### Check ingress status
```bash
kubectl get ingress -n essen-api
```

## Cleanup

To completely remove the deployment:

```bash
# Delete all resources
kubectl delete namespace essen-api

# This will remove:
# - Deployment
# - Service
# - Ingress
# - Middleware
# - PVC (and all cached data)
```

## Directory Structure

```
deploy/
├── docker/
│   ├── Dockerfile          # Multi-stage Docker build
│   ├── .dockerignore       # Exclude unnecessary files
│   └── build.sh           # Build and push helper script
├── k8s/
│   ├── namespace.yaml     # essen-api namespace
│   ├── pvc.yaml           # 5Gi persistent storage
│   ├── deployment.yaml    # API deployment with PVC mount
│   ├── service.yaml       # ClusterIP service
│   ├── middleware.yaml    # Traefik HTTPS redirect
│   ├── ingress.yaml       # Public domain ingress
│   └── apply.sh          # Apply all manifests
└── README.md             # This file
```

## Related Documentation

- [Project README](../README.md) - Overall project documentation
- [API Source Code](../src/api/) - FastAPI application code
- [CLI Tools](../src/steps/) - Original CLI implementations
- [Server Setup](../../server/) - Server infrastructure documentation
