# TraceGaurd Level 4 — Scalability, Reliability & Enterprise Readiness

TraceGaurd now includes an enterprise runtime layer designed for horizontal scaling and continuous operation.

## 1. High-traffic architecture

```text
Internet
   |
HTTPS Ingress / Load Balancer
   |
TraceGaurd Web + API
   |---------------------------|
   |                           |
Redis distributed cache     PostgreSQL
   |                           |
   +-----------+---------------+
               |
        Prometheus metrics
               |
            Grafana
```

The API is stateless at the application layer so Kubernetes can run multiple replicas. Persistent state belongs in PostgreSQL; Redis is used for distributed short-TTL caching when `REDIS_URL` is configured.

## 2. Auto-scaling

`k8s/backend.yaml` provides:

- 3 minimum API replicas
- 10 maximum replicas
- CPU and memory HPA targets
- zero unavailable replicas during rolling updates
- PodDisruptionBudget with 2 available replicas
- startup, readiness and liveness probes
- non-root container security context

## 3. Query performance

`backend/app/performance.py` creates indexes for the high-volume access paths:

- client status and creation time
- incident client/status + creation time
- incident-event lookup by incident and timestamp
- audit history by creation time
- approval and remediation history by incident and creation time

PostgreSQL also receives `ANALYZE` during enterprise bootstrap.

## 4. Caching

`backend/app/enterprise.py` provides a Redis-backed cache with an in-process fallback. Short TTLs are deliberately used for dashboard lists and metrics so the UI remains responsive without allowing stale incident state to persist for long periods.

The runtime exposes cache hits, misses and hit ratio as Prometheus metrics.

## 5. Reliability

- `/health/live` checks process liveness.
- `/health/ready` checks database readiness and reports cache state.
- Docker has a container healthcheck.
- Kubernetes probes prevent traffic from reaching an unhealthy replica.
- Rolling deployments keep capacity available.
- PDB protects against voluntary disruption of too many API replicas.

## 6. Monitoring and alerting

Prometheus is configured to scrape `/metrics` every 15 seconds. Grafana is provisioned with an operations dashboard covering:

- monitored clients
- active incidents
- request rate
- 5xx error ratio
- p95 latency
- cache hit ratio

Alert rules cover sustained API error rates, high latency, missing client inventory and cache degradation.

## 7. Security hardening

The enterprise middleware adds:

- per-IP request throttling
- request IDs
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- strict referrer policy
- GZip compression

The existing authentication, client credentials, human approval gate and allow-listed remediation controls remain in place.

## 8. Run the complete enterprise stack

```bash
docker compose -f docker-compose.enterprise.yml up --build
```

Endpoints:

- Application: `http://localhost:8080`
- API: `http://localhost:8000`
- API readiness: `http://localhost:8000/health/ready`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

Change all example passwords and secrets before exposing the stack to the public internet.

## 9. Kubernetes deployment

Build and publish the images through GitHub Actions, then configure real secrets and your domain in `k8s/`.

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/data.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/monitoring.yaml
kubectl apply -f k8s/ingress.yaml
kubectl -n tracegaurd get pods
kubectl -n tracegaurd get hpa
```

For production, use a managed PostgreSQL service and managed Redis where available instead of relying on the included single-replica demo data services.

## 10. CI/CD

GitHub Actions now runs backend tests, frontend builds, and container builds. Main-branch builds publish the API and web images to GHCR for Kubernetes rollout.
