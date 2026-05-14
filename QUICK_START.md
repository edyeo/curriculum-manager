# Quick Start Guide

Get curriculum-manager running in 5 minutes.

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Make (optional)

## One-Command Setup

```bash
make setup
```

This will:
1. Check Docker, Python, kubectl
2. Create .env.local
3. Install Python dependencies
4. Create data directories
5. Start all services

## Manual Setup

### 1. Environment Variables

```bash
cat > .env.local << 'EOF'
OPENAI_API_KEY=sk-your-key-here
DB_TYPE=file
LOG_LEVEL=DEBUG
REDIS_HOST=redis
REDIS_PORT=6379
EOF
```

### 2. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### 3. Start Services

```bash
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml up -d
```

### 4. Verify Services

```bash
# Wait ~10 seconds for startup
make check-health

# Or manually
curl http://localhost:9000/health
curl http://localhost:8001/health
```

## Service URLs

- **API Gateway**: http://localhost:9000
- **Curriculum Manager**: http://localhost:8001
- **Mental Model Manager**: http://localhost:8002
- **Researcher**: http://localhost:8003
- **Question Generator**: http://localhost:8004
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Common Commands

```bash
# Run tests
make test

# Code quality
make lint

# Code formatting
make format

# View logs
make docker-logs

# Logs for specific service
make docker-logs-curriculum-manager

# Database shell
make db-shell

# Redis CLI
make redis-cli

# Stop services
make docker-down

# Clean everything
make clean
```

## Test the API

```bash
# Check gateway health
curl http://localhost:9000/health | jq '.'

# Generate curriculum (example)
curl -X POST http://localhost:9000/curriculum/generate \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Python Programming",
    "level": "beginner",
    "duration_hours": 40
  }' | jq '.'
```

## Development Workflow

```bash
# 1. Make changes to code
vim agents/curriculum-manager/src/harness.py

# 2. Run tests
make test

# 3. Check code quality
make lint

# 4. Format code
make format

# 5. Restart affected service
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml restart curriculum-manager

# 6. View logs
make docker-logs-curriculum-manager
```

## Database Access

### Using File-based (Default)

Data is stored in JSON files:
- `nodes.json` - Curriculum entities
- `edges.json` - Relationships
- `questions.json` - Assessment questions
- `research_results.json` - Research data

### Using PostgreSQL

```bash
# Connect to database
make db-shell

# Run SQL
SELECT * FROM entities LIMIT 5;
SELECT * FROM edges LIMIT 5;
SELECT * FROM questions LIMIT 5;
```

### Backup Data

```bash
# Backup PostgreSQL
make db-backup

# Lists as: backup_20260514_143022.sql
```

## Docker Tips

```bash
# View all services
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml ps

# View specific logs
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml logs curriculum-manager -f

# Access service shell
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml exec curriculum-manager /bin/bash

# Restart service
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml restart curriculum-manager

# Stop all
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml down

# Remove volumes (reset data)
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml down -v
```

## Troubleshooting

### Services won't start

```bash
# Check Docker daemon
docker ps

# Rebuild images
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml build

# Check logs
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml logs
```

### Port already in use

```bash
# Find service using port
lsof -i :8001

# Kill service
kill -9 <PID>

# Or use different port in docker-compose.local.yml
```

### Database connection error

```bash
# Verify PostgreSQL is running
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml ps postgres

# Check connection
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml exec postgres pg_isready
```

### Redis connection error

```bash
# Verify Redis is running
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml ps redis

# Test connection
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml exec redis redis-cli ping
```

## Configuration

### Environment Variables

Edit `.env.local`:

```bash
# API Keys
OPENAI_API_KEY=sk-xxx

# Database
DB_TYPE=file  # or postgres
DB_HOST=postgres
DB_PORT=5432
DB_NAME=curriculum_db
DB_USER=curriculum_user
DB_PASSWORD=curriculum_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Logging
LOG_LEVEL=DEBUG  # or INFO, WARNING
```

### Docker Compose

Edit `infra/docker-compose.local.yml`:

```yaml
services:
  curriculum-manager:
    ports:
      - "8001:8001"  # Change to 8010:8001 for different port
    environment:
      DB_TYPE: file  # Change to postgres
```

## Next Steps

1. **Read the code**: Start with `agents/curriculum-manager/src/harness.py`
2. **Explore APIs**: Use `curl` or Postman to call endpoints
3. **Run tests**: `make test` to verify setup
4. **Check logs**: `make docker-logs` to understand flow
5. **Read docs**: See `DEPLOYMENT.md` for full documentation

## Need Help?

- Check logs: `make docker-logs`
- Read DEPLOYMENT.md: Full deployment guide
- Read PHASE_COMPLETION_SUMMARY.md: Architecture overview
- Check Makefile: Available commands with `make help`

## Cleanup

```bash
# Stop services
make docker-down

# Remove all data
make clean

# Full reset
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml down -v
```
