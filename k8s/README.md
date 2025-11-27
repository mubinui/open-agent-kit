# Kubernetes Deployment Manifests

This directory contains Kubernetes manifests for deploying the Orchestration Service.

## Quick Start

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Apply configurations
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml

# Deploy infrastructure
kubectl apply -f postgres-statefulset.yaml
kubectl apply -f redis-statefulset.yaml
kubectl apply -f rabbitmq-statefulset.yaml

# Deploy services
kubectl apply -f service.yaml

# Deploy application
kubectl apply -f deployment.yaml

# Configure ingress
kubectl apply -f ingress.yaml

# Enable autoscaling
kubectl apply -f hpa.yaml

# Apply network policies (optional)
kubectl apply -f networkpolicy.yaml
```

## Files

- **namespace.yaml** - Creates the `orchestration` namespace
- **configmap.yaml** - Application configuration (non-sensitive)
- **secret.yaml** - Sensitive configuration (API keys, passwords)
- **deployment.yaml** - Main application deployment with init containers
- **service.yaml** - Services for all components
- **ingress.yaml** - Ingress configuration with TLS
- **postgres-statefulset.yaml** - PostgreSQL StatefulSet
- **redis-statefulset.yaml** - Redis StatefulSet
- **rabbitmq-statefulset.yaml** - RabbitMQ StatefulSet
- **hpa.yaml** - Horizontal Pod Autoscaler
- **networkpolicy.yaml** - Network policies for security

## Prerequisites

- Kubernetes cluster 1.27+
- kubectl configured
- Ingress controller (NGINX recommended)
- cert-manager (for TLS certificates)
- Storage class for persistent volumes

## Configuration

### Update Secrets

Before deploying, update `secret.yaml` with your actual credentials:

```bash
# Generate base64 encoded values
echo -n "your-api-key" | base64

# Or use kubectl to create secret
kubectl create secret generic orchestration-secrets \
  --from-literal=OPENROUTER_API_KEY=your-key \
  --from-literal=OPENAI_API_KEY=your-key \
  --from-literal=JWT_SECRET_KEY=your-secret \
  --from-literal=ENCRYPTION_KEY=your-key \
  -n orchestration --dry-run=client -o yaml > secret.yaml
```

### Update Ingress

Edit `ingress.yaml` to set your domain:

```yaml
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: orchestration-tls
  rules:
  - host: your-domain.com
```

## Verification

```bash
# Check all pods are running
kubectl get pods -n orchestration

# Check services
kubectl get svc -n orchestration

# Check ingress
kubectl get ingress -n orchestration

# View logs
kubectl logs -n orchestration -l app=orchestration-service -f

# Test health endpoint
kubectl port-forward -n orchestration svc/orchestration-service 8000:8000
curl http://localhost:8000/health
```

## Scaling

### Manual Scaling

```bash
kubectl scale deployment orchestration-service -n orchestration --replicas=5
```

### Autoscaling

The HPA automatically scales based on CPU and memory:

```bash
# Check HPA status
kubectl get hpa -n orchestration

# Describe HPA
kubectl describe hpa orchestration-service-hpa -n orchestration
```

## Maintenance

### Database Migrations

```bash
# Run migrations
kubectl exec -n orchestration -it deployment/orchestration-service -- alembic upgrade head

# Check current version
kubectl exec -n orchestration -it deployment/orchestration-service -- alembic current
```

### Backup

```bash
# Backup PostgreSQL
kubectl exec -n orchestration statefulset/postgres -- pg_dump -U orchestrator orchestration > backup.sql

# Backup Redis
kubectl exec -n orchestration statefulset/redis -- redis-cli SAVE
kubectl cp orchestration/redis-0:/data/dump.rdb ./redis-backup.rdb
```

### Updates

```bash
# Update image
kubectl set image deployment/orchestration-service \
  orchestration-service=orchestration-service:v1.1.0 \
  -n orchestration

# Check rollout status
kubectl rollout status deployment/orchestration-service -n orchestration

# Rollback if needed
kubectl rollout undo deployment/orchestration-service -n orchestration
```

## Monitoring

### Prometheus

Add ServiceMonitor for Prometheus Operator:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: orchestration-service
  namespace: orchestration
spec:
  selector:
    matchLabels:
      app: orchestration-service
  endpoints:
  - port: metrics
    interval: 30s
```

### Grafana

Import the dashboard:

```bash
kubectl create configmap grafana-dashboard-orchestration \
  --from-file=../dashboards/orchestration-service.json \
  -n monitoring
```

## Troubleshooting

See [Troubleshooting Guide](../docs/troubleshooting.md) for common issues.

### Quick Checks

```bash
# Check pod status
kubectl get pods -n orchestration

# View pod logs
kubectl logs -n orchestration <pod-name>

# Describe pod
kubectl describe pod -n orchestration <pod-name>

# Check events
kubectl get events -n orchestration --sort-by='.lastTimestamp'

# Execute commands in pod
kubectl exec -n orchestration -it deployment/orchestration-service -- /bin/sh
```

## Cleanup

```bash
# Delete all resources
kubectl delete namespace orchestration

# Or delete individually
kubectl delete -f .
```

## Security

### Network Policies

Network policies restrict traffic between pods:

```bash
# Apply network policies
kubectl apply -f networkpolicy.yaml

# Test connectivity
kubectl run -n orchestration test-pod --image=busybox --rm -it -- sh
```

### RBAC

The deployment uses a dedicated ServiceAccount with minimal permissions.

### Secrets Management

For production, use external secret management:

- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault
- Kubernetes External Secrets Operator

## Additional Resources

- [Deployment Guide](../docs/deployment-guide.md)
- [Environment Variables](../docs/environment-variables.md)
- [Troubleshooting](../docs/troubleshooting.md)
