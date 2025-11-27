# Orchestration Service - Deployment Quick Reference

Quick reference for deploying the Orchestration Service.

## Prerequisites

- Docker 24.0+
- Python 3.11+
- PostgreSQL 16+, Redis 7+, RabbitMQ 3.12+ (or use Docker Compose)
- Kubernetes 1.27+ and Helm 3.12+ (for production)

## Quick Start Options

### 1. Docker Compose (Recommended for Development)

```bash
# 1. Set environment variables
cp .env.example .env
# Edit .env with your API keys

# 2. Start all services
docker-compose up -d

# 3. Run migrations
docker-compose exec orchestration-service alembic upgrade head

# 4. Access the service
curl http://localhost:8000/health
```

**Services**:
- API: http://localhost:8000
- Metrics: http://localhost:9090/metrics
- RabbitMQ Management: http://localhost:15672

### 2. Docker (Standalone)

```bash
# Build image
docker build -t orchestration-service:latest .

# Run container (requires external PostgreSQL, Redis, RabbitMQ)
docker run -d \
  --name orchestration-service \
  -p 8000:8000 \
  -p 9090:9090 \
  -e OPENROUTER_API_KEY=your-key \
  -e DATABASE_URL=postgresql://user:pass@host:5432/orchestration \
  -e REDIS_URL=redis://host:6379/0 \
  -e RABBITMQ_URL=amqp://user:pass@host:5672/ \
  orchestration-service:latest
```

### 3. Kubernetes with Helm (Production)

```bash
# Install with Helm
helm install orchestration-service ./helm/orchestration-service \
  --namespace orchestration \
  --create-namespace \
  --values ./helm/orchestration-service/values-prod.yaml \
  --set secrets.openrouterApiKey=$OPENROUTER_API_KEY

# Check status
kubectl get pods -n orchestration
helm status orchestration-service -n orchestration
```

### 4. Kubernetes with Raw Manifests

```bash
# Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml  # Update with your secrets first!
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/redis-statefulset.yaml
kubectl apply -f k8s/rabbitmq-statefulset.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

## Required Environment Variables

```bash
# LLM Providers (at least one required)
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENAI_API_KEY=sk-xxxxx  # Optional

# Infrastructure - Core Services
DATABASE_URL=postgresql://user:pass@host:5432/orchestration
REDIS_URL=redis://host:6379/0

# Infrastructure - Message Broker (Optional, for async processing)
RABBITMQ_URL=amqp://user:pass@host:5672/
RABBITMQ_MAX_CONNECTIONS=10
RABBITMQ_MAX_CHANNELS=100

# Infrastructure - Vector Databases (Optional, for RAG features)
CHROMADB_PATH=./data/chromadb
QDRANT_URL=http://host:6333
QDRANT_API_KEY=your-qdrant-key  # For Qdrant Cloud
PGVECTOR_URL=postgresql://user:pass@host:5432/vectordb

# Security
SECRET_KEY=your-secure-random-string-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=your-32-byte-encryption-key-base64

# Application Settings
LOG_LEVEL=INFO
ENVIRONMENT=production
MAX_CONVERSATION_TURNS=20
RESPONSE_TIMEOUT_SECONDS=30

# Observability (Optional)
ENABLE_TELEMETRY=true
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
OTLP_ENDPOINT=http://collector:4317  # For distributed tracing
```

## Configuration Management

### Configuration Files Location

All JSON configuration files should be mounted to `/app/configs` in the container:

```bash
# Docker Compose (already configured in docker-compose.yml)
volumes:
  - ./configs:/app/configs

# Docker Run
docker run -d \
  -v $(pwd)/configs:/app/configs \
  orchestration-service:latest

# Kubernetes ConfigMap
kubectl create configmap orchestration-configs \
  --from-file=configs/ \
  -n orchestration
```

### Environment-Specific Configurations

**Development:**
- Hot-reload enabled automatically
- Debug logging
- Detailed error messages
- CORS allows all origins

**Production:**
- Hot-reload disabled (restart required for config changes)
- INFO/WARNING logging only
- Generic error messages
- CORS restricted to specific origins
- Rate limiting enforced
- Authentication required

### Updating Configurations in Production

**Option 1: Via REST API (Recommended)**
```bash
# Update agent configuration
curl -X PUT https://api.example.com/api/v1/agents/my_agent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"system_message": "Updated prompt"}'

# Reload configurations (no restart needed)
curl -X POST https://api.example.com/api/v1/configs/reload \
  -H "Authorization: Bearer $TOKEN"
```

**Option 2: Update ConfigMap (Kubernetes)**
```bash
# Update ConfigMap
kubectl create configmap orchestration-configs \
  --from-file=configs/ \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up changes
kubectl rollout restart deployment orchestration-service -n orchestration
```

**Option 3: Mount Volume (Docker)**
```bash
# Edit local files
nano configs/agents.json

# Restart container
docker restart orchestration-service
```

## Verification

```bash
# Health check
curl http://localhost:8000/health

# Metrics
curl http://localhost:9090/metrics

# Create a session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "default"}'
```

## Documentation

- **[Deployment Guide](docs/deployment-guide.md)** - Complete deployment instructions
- **[Environment Variables](docs/environment-variables.md)** - All configuration options
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[Kubernetes README](k8s/README.md)** - Kubernetes-specific instructions
- **[Helm README](helm/README.md)** - Helm chart documentation

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Orchestration Service                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  FastAPI     │  │  Autogen     │  │  Admin UI    │  │
│  │  REST API    │  │  Agents      │  │  (Angular)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
│  PostgreSQL  │  │    Redis    │  │  RabbitMQ   │
│  (Sessions)  │  │   (Cache)   │  │  (Async)    │
└──────────────┘  └─────────────┘  └─────────────┘
```

## Scaling

### Horizontal Scaling

```bash
# Docker Compose
docker-compose up -d --scale orchestration-service=3

# Kubernetes
kubectl scale deployment orchestration-service -n orchestration --replicas=5

# Helm (update values)
helm upgrade orchestration-service ./helm/orchestration-service \
  --set replicaCount=5 \
  --reuse-values
```

### Autoscaling (Kubernetes)

HPA automatically scales based on CPU/memory (configured in `k8s/hpa.yaml` or Helm values).

## Monitoring

### Prometheus Metrics

Available at `/metrics` endpoint:
- HTTP request metrics
- Agent conversation metrics
- LLM API call metrics
- Cache hit/miss rates
- Queue depths

### Grafana Dashboard

Import the dashboard from `dashboards/orchestration-service.json`.

### Logs

```bash
# Docker Compose
docker-compose logs -f orchestration-service

# Kubernetes
kubectl logs -n orchestration -l app=orchestration-service -f
```

## Maintenance

### Database Migrations

```bash
# Docker Compose
docker-compose exec orchestration-service alembic upgrade head

# Kubernetes
kubectl exec -n orchestration -it deployment/orchestration-service -- alembic upgrade head
```

### Backup

```bash
# PostgreSQL
pg_dump $DATABASE_URL > backup.sql

# Redis
redis-cli SAVE
cp /data/dump.rdb backup.rdb
```

### Updates

```bash
# Docker Compose
docker-compose pull
docker-compose up -d

# Kubernetes with Helm
helm upgrade orchestration-service ./helm/orchestration-service \
  --set image.tag=v1.1.0 \
  --reuse-values
```

## Support

- **Documentation**: See `docs/` directory
- **Issues**: GitHub Issues
- **Email**: support@example.com

## Security Notes

⚠️ **Important**:
1. Never commit `.env` files or secrets to version control
2. Use strong, random values for JWT_SECRET_KEY and ENCRYPTION_KEY
3. Use external secret management (AWS Secrets Manager, Azure Key Vault) in production
4. Enable TLS/HTTPS for all external traffic
5. Regularly update dependencies and base images
6. Review and apply security patches promptly

## Next Steps

1. Review [Deployment Guide](docs/deployment-guide.md) for detailed instructions
2. Configure [Environment Variables](docs/environment-variables.md)
3. Set up monitoring and alerting
4. Configure backups
5. Test disaster recovery procedures
6. Review [Troubleshooting Guide](docs/troubleshooting.md)
