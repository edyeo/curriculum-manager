.PHONY: help setup install test lint format clean docker-build docker-up docker-down docker-restart docker-health docker-logs docker-logs- build-cm up-cm k8s-deploy k8s-delete terraform-init terraform-plan terraform-apply

COMPOSE = docker compose --env-file ../.env -f infra/docker-compose.yml -f infra/docker-compose.local.yml

help:
	@echo "curriculum-manager development commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup           - Complete setup (dependencies, docker, databases)"
	@echo "  make install         - Install Python dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make test            - Run test suite"
	@echo "  make lint            - Run linting checks"
	@echo "  make format          - Format code with black and isort"
	@echo "  make clean           - Clean build artifacts and cache"
	@echo ""
	@echo "Docker & Local:"
	@echo "  make docker-build    - Build all Docker images"
	@echo "  make docker-up       - Start all services with docker-compose"
	@echo "  make docker-down     - Stop all services"
	@echo "  make docker-logs     - View docker-compose logs"
	@echo ""
	@echo "Kubernetes:"
	@echo "  make k8s-deploy      - Deploy to Kubernetes cluster"
	@echo "  make k8s-delete      - Delete Kubernetes resources"
	@echo "  make k8s-logs        - View pod logs"
	@echo ""
	@echo "Terraform (IaC):"
	@echo "  make terraform-init  - Initialize Terraform"
	@echo "  make terraform-plan  - Plan infrastructure changes"
	@echo "  make terraform-apply - Apply infrastructure changes"

# Setup & Installation
setup:
	@echo "Running complete setup..."
	@cd infra && bash setup.sh

install:
	python -m pip install --upgrade pip
	pip install -e ".[dev]"

# Testing & Quality
test:
	./.venv/bin/pytest tests/ -v --cov=agents --cov=shared --cov-report=html

lint:
	./.venv/bin/ruff check agents/ apps/ shared/
	./.venv/bin/mypy agents/ apps/ shared/ --ignore-missing-imports

format:
	./.venv/bin/black agents/ apps/ shared/ tests/
	./.venv/bin/isort agents/ apps/ shared/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/
	$(COMPOSE) down -v

# Docker Commands
docker-build:
	$(COMPOSE) build

docker-up:
	$(COMPOSE) up -d
	@echo "Services starting. Check health with: make docker-health"

docker-down:
	$(COMPOSE) down


docker-restart: docker-down docker-up

# Contents Manager만 재빌드·재시작
build-cm:
	$(COMPOSE) build --no-cache contents-manager-backend contents-manager-frontend

up-cm:
	$(COMPOSE) up -d --force-recreate contents-manager-backend contents-manager-frontend

docker-health:
	$(COMPOSE) ps

docker-logs:
	$(COMPOSE) logs -f

docker-logs-%:
	$(COMPOSE) logs -f $*

docker-shell-%:
	$(COMPOSE) exec $* /bin/sh

# Kubernetes Commands
k8s-namespace:
	kubectl apply -f infra/k8s/namespace.yaml

k8s-secrets:
	kubectl apply -f infra/k8s/secrets.yaml

k8s-deploy: k8s-namespace k8s-secrets
	kubectl apply -f infra/k8s/
	kubectl rollout status deployment -n curriculum --timeout=5m

k8s-delete:
	kubectl delete -f infra/k8s/
	kubectl delete namespace curriculum

k8s-logs:
	kubectl logs -f deployment/curriculum-manager -n curriculum

k8s-status:
	kubectl get all -n curriculum

k8s-describe-%:
	kubectl describe pod/$* -n curriculum

# Terraform Commands
terraform-init:
	cd infra/terraform && terraform init

terraform-plan:
	cd infra/terraform && terraform plan -var-file="environments/dev.tfvars" -out=tfplan

terraform-apply:
	cd infra/terraform && terraform apply tfplan

terraform-destroy:
	cd infra/terraform && terraform destroy -var-file="environments/dev.tfvars"

terraform-output:
	cd infra/terraform && terraform output

# Development helpers
run-agent-%:
	AGENT=$* python -m apps.$*.main

check-health:
	@echo "=== Agent Platform ==="
	@curl -sf http://localhost:8001/health | jq '.' 2>/dev/null || echo "curriculum-manager: DOWN"
	@curl -sf http://localhost:8002/health | jq '.' 2>/dev/null || echo "mental-model-manager: DOWN"
	@curl -sf http://localhost:8003/health | jq '.' 2>/dev/null || echo "researcher: DOWN"
	@curl -sf http://localhost:8004/health | jq '.' 2>/dev/null || echo "question-generator: DOWN"
	@curl -sf http://localhost:9000/health | jq '.' 2>/dev/null || echo "api-gateway: DOWN"
	@echo "=== Contents Manager ==="
	@curl -sf http://localhost:8010/api/health | jq '.' 2>/dev/null || echo "cm-backend: DOWN"
	@curl -sf http://localhost:3000 -o /dev/null -w "cm-frontend: HTTP %{http_code}\n" 2>/dev/null || echo "cm-frontend: DOWN"

generate-curriculum:
	curl -X POST http://localhost:9000/curriculum/generate \
		-H "Content-Type: application/json" \
		-d '{
			"subject": "Python Programming",
			"level": "beginner",
			"duration_hours": 40
		}' | jq '.'

generate-questions:
	curl -X POST http://localhost:9000/api/questions/generate \
		-H "Content-Type: application/json" \
		-d '{
			"entity_id": "concept-001",
			"count": 5,
			"difficulty": "medium"
		}' | jq '.'

# Database
db-migrate:
	$(COMPOSE) exec postgres \
		psql -U curriculum_user -d curriculum_db -f /docker-entrypoint-initdb.d/01_knowledge_graph.sql

db-shell:
	$(COMPOSE) exec postgres \
		psql -U curriculum_user -d curriculum_db

db-backup:
	$(COMPOSE) exec postgres \
		pg_dump -U curriculum_user curriculum_db > backup_$(shell date +%Y%m%d_%H%M%S).sql

redis-cli:
	$(COMPOSE) exec redis \
		redis-cli
