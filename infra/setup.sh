#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker."
        exit 1
    fi
    print_info "Docker found: $(docker --version)"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        if docker compose version &> /dev/null 2>&1; then
            print_warn "docker-compose not found, using 'docker compose' plugin instead."
            docker-compose() { docker compose "$@"; }
            export -f docker-compose
            print_info "Docker Compose (plugin) found: $(docker compose version --short)"
        else
            print_error "Docker Compose is not installed. Please install Docker Compose."
            exit 1
        fi
    else
        print_info "Docker Compose found: $(docker-compose --version)"
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.11 or later."
        exit 1
    fi
    python_version=$(python3 --version | cut -d' ' -f2)
    print_info "Python found: $python_version"

    # Check kubectl (optional for local development)
    if ! command -v kubectl &> /dev/null; then
        print_warn "kubectl is not installed. You won't be able to deploy to Kubernetes locally."
    else
        print_info "kubectl found: $(kubectl version --client 2>/dev/null | head -1 || echo 'installed')"
    fi
}

# Setup environment variables
setup_env() {
    print_info "Setting up environment variables..."

    if [ ! -f .env.local ]; then
        cat > .env.local << EOF
# Local Development Environment Variables
OPENAI_API_KEY=sk-your-key-here
DB_TYPE=file
LOG_LEVEL=DEBUG

# For PostgreSQL (uncomment if using PostgreSQL)
# DB_TYPE=postgres
# DB_HOST=postgres
# DB_PORT=5432
# DB_NAME=curriculum_db
# DB_USER=curriculum_user
# DB_PASSWORD=curriculum_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
EOF
        print_info "Created .env.local. Please update OPENAI_API_KEY."
    else
        print_info ".env.local already exists. Skipping creation."
    fi
}

# Setup Python dependencies
setup_python() {
    print_info "Installing Python dependencies..."

    cd ..
    uv sync --extra dev
    cd infra

    print_info "Python dependencies installed."
}

# Create data directories
setup_data_dirs() {
    print_info "Creating data directories..."

    mkdir -p data/{nodes,edges,questions,responses,research_results}
    print_info "Data directories created."
}

# Start services
start_services() {
    print_info "Starting services with Docker Compose..."

    docker-compose -f docker-compose.yml -f docker-compose.local.yml up -d

    print_info "Waiting for services to be ready..."
    sleep 10

    # Check if all services are healthy
    for service in postgres redis curriculum-manager mental-model-manager researcher question-generator gateway; do
        if docker-compose ps | grep -q "$service.*healthy"; then
            print_info "$service is healthy"
        else
            print_warn "$service might not be fully ready yet"
        fi
    done
}

# Initialize database
init_database() {
    print_info "Initializing database..."

    # Wait for PostgreSQL to be ready
    until docker-compose exec -T postgres pg_isready -U curriculum_user > /dev/null 2>&1; do
        echo "Waiting for PostgreSQL to be ready..."
        sleep 2
    done

    # Run migrations (if using PostgreSQL)
    # docker-compose exec postgres psql -U curriculum_user -d curriculum_db -f /docker-entrypoint-initdb.d/01_knowledge_graph.sql

    print_info "Database initialized."
}

# Print next steps
print_next_steps() {
    cat << EOF

${GREEN}✓ Setup complete!${NC}

Next steps:

1. Update .env.local with your OPENAI_API_KEY

2. Start services:
   docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml up -d

3. Check service health:
   docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml ps

4. View logs:
   docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml logs -f [service-name]

5. Access services:
   - API Gateway: http://localhost:9000
   - Curriculum Manager: http://localhost:8001
   - Mental Model Manager: http://localhost:8002
   - Researcher: http://localhost:8003
   - Question Generator: http://localhost:8004
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

6. Run tests:
   source .venv/bin/activate
   pytest tests/ -v

7. Stop services:
   docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml down

For more information, see the README.md file.
EOF
}

# Main
main() {
    print_info "Starting setup for curriculum-manager..."
    check_prerequisites
    setup_env
    setup_python
    setup_data_dirs
    start_services
    init_database
    print_next_steps
}

# Run main function
main
