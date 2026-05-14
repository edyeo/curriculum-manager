# Deployment Guide

This guide covers setting up and deploying the curriculum-manager multi-agent system across different environments.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  API Gateway (Port 9000)             │
│         Central orchestration & request routing      │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┼────────────┬─────────────────┐
        │            │            │                 │
   ┌────▼──┐   ┌────▼──┐   ┌────▼──┐   ┌────▼──┐
   │Curr.  │   │Mental │   │Resear │   │Questi │
   │Mgr    │   │Model  │   │cher   │   │on Gen │
   │:8001  │   │:8002  │   │:8003  │   │:8004  │
   └───┬───┘   └───┬───┘   └───┬───┘   └───┬───┘
       │           │           │           │
       └───────────┼───────────┼───────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
    ┌───▼──┐   ┌──▼──┐   ┌───▼──┐
    │ Pg   │   │Redis│   │File  │
    │SQL   │   │     │   │Store │
    │:5432 │   │:6379│   │(JSON)│
    └──────┘   └─────┘   └──────┘
```

## Local Development Setup

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- kubectl (optional, for K8s testing)
- Terraform (optional, for infrastructure management)
- Make (optional, for command shortcuts)

### Quick Start

```bash
# Clone and setup
git clone <repo>
cd curriculum-manager
make setup

# Activate Python environment
source venv/bin/activate

# Start all services
make docker-up

# Check service health
make check-health

# View logs
make docker-logs
```

### Environment Variables

Create `.env.local` in the project root:

```bash
# API Keys
OPENAI_API_KEY=sk-your-key-here

# Database
DB_TYPE=file  # or 'postgres' for production-like setup
DB_HOST=postgres
DB_PORT=5432
DB_NAME=curriculum_db
DB_USER=curriculum_user
DB_PASSWORD=curriculum_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Logging
LOG_LEVEL=DEBUG
```

### Local Service Access

| Service | URL | Port |
|---------|-----|------|
| API Gateway | http://localhost:9000 | 9000 |
| Curriculum Manager | http://localhost:8001 | 8001 |
| Mental Model Manager | http://localhost:8002 | 8002 |
| Researcher | http://localhost:8003 | 8003 |
| Question Generator | http://localhost:8004 | 8004 |
| PostgreSQL | localhost:5432 | 5432 |
| Redis | localhost:6379 | 6379 |

### Common Development Tasks

```bash
# Run tests
make test

# Code quality checks
make lint

# Format code
make format

# View Docker logs
make docker-logs-[service-name]

# Access database
make db-shell

# Access Redis CLI
make redis-cli
```

## Kubernetes Deployment

### Prerequisites

- EKS cluster (or any Kubernetes 1.29+)
- kubectl configured
- Docker images pushed to registry

### Deploy to Kubernetes

```bash
# Apply Kubernetes manifests
make k8s-deploy

# Check deployment status
make k8s-status

# View logs
make k8s-logs

# Delete deployments
make k8s-delete
```

### Kubernetes Architecture

```yaml
# Namespace
namespace: curriculum

# Services
- curriculum-manager (ClusterIP:8001)
- mental-model-manager (ClusterIP:8002)
- researcher (ClusterIP:8003)
- question-generator (ClusterIP:8004)
- api-gateway (LoadBalancer:9000)
- postgres (ClusterIP:5432)

# Deployments
- curriculum-manager: 2 replicas
- mental-model-manager: 1 replica
- researcher: 1 replica
- question-generator: 1 replica
- api-gateway: 1 replica
- postgres-statefulset: 1 replica (persistent storage)

# Storage
- PostgreSQL PVC: 10Gi
```

## Infrastructure as Code (Terraform)

### Setup Terraform

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Plan infrastructure
terraform plan -var-file="environments/dev.tfvars" -out=tfplan

# Apply configuration
terraform apply tfplan

# View outputs
terraform output
```

### Terraform Environments

#### Development (`dev.tfvars`)
- 2 EC2 nodes (t3.medium)
- PostgreSQL: t3.micro
- Redis: t3.micro (1 node)
- Storage: 20GB → 50GB autoscaling

#### Staging (`staging.tfvars`)
- 3 EC2 nodes (t3.small)
- PostgreSQL: t3.small
- Redis: t3.small (2 nodes)
- Storage: 50GB → 200GB autoscaling

#### Production (`prod.tfvars`)
- 5 EC2 nodes (t3.large)
- PostgreSQL: t3.medium with Multi-AZ
- Redis: t3.medium (3 nodes)
- Storage: 100GB → 500GB autoscaling

### Terraform Deployment

```bash
# Development
terraform apply -var-file="environments/dev.tfvars"

# Staging
terraform apply -var-file="environments/staging.tfvars"

# Production
terraform apply -var-file="environments/prod.tfvars" \
  -var db_password=$DB_PASSWORD

# Get connection details
terraform output deployment_summary
```

## CI/CD Pipeline

### GitHub Actions Workflow

The pipeline is triggered on:
- Push to `main` (production deployment)
- Push to `develop` (staging deployment)
- Pull requests (testing only)

### Pipeline Stages

1. **Test** (Python 3.11, 3.12)
   - Install dependencies
   - Lint with ruff
   - Type check with mypy
   - Run pytest with coverage

2. **Build**
   - Build Docker images for each agent
   - Push to ghcr.io

3. **Deploy to Staging** (on develop push)
   - Update EKS deployments
   - Wait for rollout

4. **Deploy to Production** (on main push)
   - Update EKS deployments
   - Notify Slack

### Required GitHub Secrets

```
AWS_ROLE_ARN_STAGING=arn:aws:iam::ACCOUNT:role/staging-role
AWS_ROLE_ARN_PRODUCTION=arn:aws:iam::ACCOUNT:role/prod-role
SLACK_WEBHOOK=https://hooks.slack.com/services/...
```

## Database Migrations

### File-based (Development)

Uses JSON files for storage:
- `nodes.json` - Entities
- `edges.json` - Relationships
- `questions.json` - Assessment questions
- `research_results.json` - Research data

### PostgreSQL (Production)

```bash
# Run migrations
make db-migrate

# Backup database
make db-backup

# Connect to database
make db-shell
```

Migration files:
- `01_knowledge_graph.sql` - Entities and edges
- `02_question_bank.sql` - Questions and responses
- `03_researcher_db.sql` - Research results

## Monitoring & Logging

### Local Development

```bash
# View logs
make docker-logs

# Check service health
make check-health

# Access health endpoints
curl http://localhost:8001/health  # Curriculum Manager
curl http://localhost:9000/health  # API Gateway
```

### Kubernetes

```bash
# Pod logs
kubectl logs -f deployment/curriculum-manager -n curriculum

# Describe pod
kubectl describe pod <pod-name> -n curriculum

# Port forward for debugging
kubectl port-forward svc/api-gateway 9000:9000 -n curriculum
```

### Production Monitoring (Recommended)

- **CloudWatch** - Logs and metrics
- **Prometheus** - Metrics scraping
- **Grafana** - Dashboards
- **ELK Stack** - Log aggregation
- **DataDog** - APM and monitoring

## Scaling

### Horizontal Scaling

```bash
# Scale deployments
kubectl scale deployment curriculum-manager --replicas=5 -n curriculum

# Autoscaling (HPA)
kubectl autoscale deployment curriculum-manager \
  --min=2 --max=10 --cpu-percent=80 -n curriculum
```

### Database Scaling

PostgreSQL automatically scales storage (up to 500GB by default).

For read-heavy workloads, add read replicas:
```bash
# Terraform: Uncomment replica configuration in main.tf
```

## Backup & Disaster Recovery

### Database Backups

```bash
# Automated: RDS has 30-day retention
# Manual backup
make db-backup

# Restore from backup
# In AWS RDS console or:
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier curriculum-db-restored \
  --db-snapshot-identifier <snapshot-id>
```

### Data Files

File-based data (`nodes.json`, etc.) is stored in volumes:

```bash
# Backup volumes
docker cp curriculum-postgres:/var/lib/postgresql/data ./postgres_backup

# Backup S3 (recommended)
aws s3 sync ./data s3://curriculum-backup/data/
```

## Troubleshooting

### Services won't start

```bash
# Check Docker daemon
docker info

# Rebuild images
make docker-build

# Check compose configuration
docker-compose -f infra/docker-compose.yml config

# View service logs
make docker-logs
```

### Database connection errors

```bash
# Verify PostgreSQL is running
make docker-health

# Test connection
make db-shell

# Check network
docker network ls
docker network inspect curriculum-network
```

### Kubernetes pod issues

```bash
# Check pod status
kubectl describe pod <pod-name> -n curriculum

# Check events
kubectl get events -n curriculum

# Port forward for debugging
kubectl port-forward pod/<pod-name> 8001:8001 -n curriculum

# Exec into pod
kubectl exec -it <pod-name> -n curriculum -- /bin/bash
```

## Security Best Practices

1. **Secrets Management**
   - Use AWS Secrets Manager or HashiCorp Vault
   - Never commit credentials to git
   - Rotate keys regularly

2. **Network Security**
   - Use Security Groups with least privilege
   - Enable VPC encryption
   - Use NLB with TLS termination

3. **Database Security**
   - Enable encryption at rest
   - Use SSL/TLS for connections
   - Regular backups and testing

4. **Container Security**
   - Use minimal base images
   - Scan for vulnerabilities
   - Run as non-root user

5. **Access Control**
   - Use IAM roles for pod authentication
   - Enable RBAC on Kubernetes
   - Implement API authentication

## Performance Optimization

### Caching Strategy

- Redis for session and frequently accessed data
- Query result caching (60-300 seconds)
- Edge caching with CloudFront

### Database Optimization

- Index frequently queried columns
- Use connection pooling
- Optimize slow queries

### Application-level

- Async processing for long operations
- Batch processing where possible
- Rate limiting on APIs

## Cost Optimization

### Development
- Use spot instances for worker nodes
- Smaller database instance (t3.micro)
- Single Redis node

### Staging
- Mix of on-demand and spot instances
- Medium database instance
- Multi-node Redis

### Production
- On-demand instances for stability
- Large database with Multi-AZ
- High-availability Redis cluster

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Docker Compose](https://docs.docker.com/compose/)
- [GitHub Actions](https://github.com/features/actions)
