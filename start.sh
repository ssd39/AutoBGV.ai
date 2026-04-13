#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

COMPOSE_INFRA="docker-compose.infra.yml"
COMPOSE_SERVICES="docker-compose.yml"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# PIDs of locally started processes (for cleanup)
declare -a LOCAL_PIDS=()

print_banner() {
  echo -e "${BLUE}"
  echo "  ___        _         ____   ______     __"
  echo " / _ \      | |       |  _ \ / ___\ \   / /"
  echo "| | | |_   _| |_ ___  | |_) | |  _ \ \ / / "
  echo "| |_| | | | | __/ _ \ |  _ <| |_| | \ V /  "
  echo " \___/ \__,_|\__\___/ |_| \_\\\\____/   \_/   "
  echo ""
  echo "  AutoBGV - Document Verification & KYC Platform"
  echo -e "${NC}"
}

print_usage() {
  echo -e "${YELLOW}Usage:${NC}"
  echo ""
  echo -e "  ${CYAN}Development (local, live-reload):${NC}"
  echo "  ./start.sh dev             - Start infra (Docker) + all services locally with live reload"
  echo "  ./start.sh dev:setup       - Set up .venv and install Python deps for all services"
  echo "  ./start.sh dev:workflow    - Start only workflow service locally (infra must be running)"
  echo "  ./start.sh dev:agent       - Start only agent service locally (infra must be running)"
  echo "  ./start.sh dev:verification - Start only verification service locally (infra must be running)"
  echo "  ./start.sh dev:frontend    - Start only frontend locally"
  echo ""
  echo -e "  ${CYAN}Docker (full containerized):${NC}"
  echo "  ./start.sh infra           - Start infrastructure only (PostgreSQL, Redis, MinIO)"
  echo "  ./start.sh up              - Start all services (infra + application services)"
  echo "  ./start.sh down            - Stop all services"
  echo "  ./start.sh down:infra      - Stop infrastructure services only"
  echo "  ./start.sh restart         - Restart all services"
  echo "  ./start.sh logs [service]  - View logs (optional: specify service name)"
  echo "  ./start.sh status          - Show status of all services"
  echo "  ./start.sh build           - Build all service images"
  echo "  ./start.sh migrate         - Run database migrations"
  echo "  ./start.sh clean           - Stop and remove all containers, volumes, and networks"
  echo ""
}

check_docker() {
  if ! command -v docker &>/dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
  fi
  if ! docker info &>/dev/null; then
    echo -e "${RED}Error: Docker daemon is not running${NC}"
    exit 1
  fi
}

check_python() {
  if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: python3 not found. Install Python 3.12+ from https://python.org${NC}"
    exit 1
  fi
  PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
  echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"
}

check_node() {
  if ! command -v node &>/dev/null; then
    echo -e "${RED}Error: node not found. Install Node.js 20+ from https://nodejs.org${NC}"
    exit 1
  fi
  NODE_VERSION=$(node --version)
  echo -e "${GREEN}✓ Node.js ${NODE_VERSION} found${NC}"
}

load_env() {
  if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo -e "${GREEN}✓ Loaded environment from .env${NC}"
  else
    echo -e "${YELLOW}⚠ No .env file found, using defaults${NC}"
    # Set sensible defaults
    export POSTGRES_USER="${POSTGRES_USER:-autobgv}"
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-autobgv_secret}"
    export POSTGRES_DB="${POSTGRES_DB:-autobgv}"
    export REDIS_PASSWORD="${REDIS_PASSWORD:-redis_secret}"
  fi
}

wait_for_infra() {
  echo -e "${YELLOW}⏳ Waiting for infrastructure to be healthy...${NC}"
  local max_wait=60
  local waited=0

  while [ $waited -lt $max_wait ]; do
    POSTGRES_HEALTHY=$(docker inspect --format='{{.State.Health.Status}}' autobgv_postgres 2>/dev/null || echo "not_found")
    REDIS_HEALTHY=$(docker inspect --format='{{.State.Health.Status}}' autobgv_redis 2>/dev/null || echo "not_found")

    if [ "$POSTGRES_HEALTHY" = "healthy" ] && [ "$REDIS_HEALTHY" = "healthy" ]; then
      echo -e "${GREEN}✓ Infrastructure is healthy!${NC}"
      return 0
    fi

    echo -ne "\r  Waiting... (${waited}s / ${max_wait}s) - Postgres: ${POSTGRES_HEALTHY}, Redis: ${REDIS_HEALTHY}"
    sleep 3
    waited=$((waited + 3))
  done

  echo -e "\n${RED}✗ Infrastructure did not become healthy in time${NC}"
  return 1
}

# ─── .venv Management ────────────────────────────────────────────────────────

setup_venv() {
  local service=$1
  local service_dir="${ROOT_DIR}/services/${service}"
  local venv_dir="${service_dir}/.venv"

  echo -e "${CYAN}📦 Setting up .venv for ${service}...${NC}"

  if [ ! -d "$venv_dir" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv "$venv_dir"
    echo -e "  ${GREEN}✓ .venv created${NC}"
  else
    echo -e "  ${GREEN}✓ .venv already exists${NC}"
  fi

  echo "  Installing/updating dependencies..."
  "$venv_dir/bin/pip" install --quiet --upgrade pip
  "$venv_dir/bin/pip" install --quiet -r "${service_dir}/requirements.txt"
  echo -e "  ${GREEN}✓ Dependencies installed${NC}"
}

setup_all_venvs() {
  check_python
  echo ""
  setup_venv "workflow"
  echo ""
  setup_venv "agent"
  echo ""
  setup_venv "verification"
  echo ""
  echo -e "${GREEN}✓ All .venv environments ready!${NC}"
}

# ─── Local Service Starters ──────────────────────────────────────────────────

start_workflow_local() {
  local service_dir="${ROOT_DIR}/services/workflow"
  local venv_python="${service_dir}/.venv/bin/python"

  if [ ! -f "$venv_python" ]; then
    echo -e "${YELLOW}⚠ .venv not found for workflow. Running setup...${NC}"
    setup_venv "workflow"
  fi

  # Export env vars for the service
  export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER:-autobgv}:${POSTGRES_PASSWORD:-autobgv_secret}@localhost:5432/${POSTGRES_DB:-autobgv}"
  export REDIS_URL="redis://:${REDIS_PASSWORD:-redis_secret}@localhost:6379/0"
  export ENVIRONMENT="development"
  export SERVICE_PORT="8001"
  export CORS_ORIGINS="http://localhost:3000"

  echo -e "${CYAN}⚙️  Running Alembic migrations (workflow)...${NC}"
  cd "$service_dir"
  .venv/bin/alembic upgrade head 2>/dev/null && echo -e "  ${GREEN}✓ Migrations up to date${NC}" || echo -e "  ${YELLOW}⚠ Migration skipped (already up to date)${NC}"
  cd "$ROOT_DIR"

  echo -e "${CYAN}⚙️  Starting Workflow Service (port 8001, live reload)...${NC}"
  cd "$service_dir"
  .venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --reload \
    --reload-dir "${service_dir}/app" \
    --log-level info &
  LOCAL_PIDS+=($!)
  echo -e "  ${GREEN}✓ PID $!${NC}"
  cd "$ROOT_DIR"
}

start_agent_local() {
  local service_dir="${ROOT_DIR}/services/agent"
  local venv_python="${service_dir}/.venv/bin/python"

  if [ ! -f "$venv_python" ]; then
    echo -e "${YELLOW}⚠ .venv not found for agent. Running setup...${NC}"
    setup_venv "agent"
  fi

  # Agent shares the same PostgreSQL DB as workflow service
  export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER:-autobgv}:${POSTGRES_PASSWORD:-autobgv_secret}@localhost:5432/${POSTGRES_DB:-autobgv}"
  # DB 1 — agent session/state storage
  export REDIS_URL="redis://:${REDIS_PASSWORD:-redis_secret}@localhost:6379/1"
  # DB 0 — shared queue, MUST match the workflow service's REDIS_URL database (/0)
  export QUEUE_REDIS_URL="redis://:${REDIS_PASSWORD:-redis_secret}@localhost:6379/0"
  export WORKFLOW_SERVICE_URL="http://localhost:8001"
  export ENVIRONMENT="development"
  export SERVICE_PORT="8002"
  export CORS_ORIGINS="http://localhost:3000"

  echo -e "${CYAN}🤖 Starting Agent Service (port 8002, live reload)...${NC}"
  cd "$service_dir"
  .venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8002 \
    --reload \
    --reload-dir "${service_dir}/app" \
    --log-level info &
  LOCAL_PIDS+=($!)
  echo -e "  ${GREEN}✓ PID $!${NC}"
  cd "$ROOT_DIR"
}

start_verification_local() {
  local service_dir="${ROOT_DIR}/services/verification"
  local venv_python="${service_dir}/.venv/bin/python"

  if [ ! -f "$venv_python" ]; then
    echo -e "${YELLOW}⚠ .venv not found for verification. Running setup...${NC}"
    setup_venv "verification"
  fi

  export REDIS_URL="redis://:${REDIS_PASSWORD:-redis_secret}@localhost:6379/2"
  export WORKFLOW_SERVICE_URL="http://localhost:8001"
  export ENVIRONMENT="development"
  export SERVICE_PORT="8003"

  echo -e "${CYAN}✅ Starting Verification Service (port 8003, live reload)...${NC}"
  cd "$service_dir"
  .venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8003 \
    --reload \
    --reload-dir "${service_dir}/app" \
    --log-level info &
  LOCAL_PIDS+=($!)
  echo -e "  ${GREEN}✓ PID $!${NC}"
  cd "$ROOT_DIR"
}

start_frontend_local() {
  local frontend_dir="${ROOT_DIR}/frontend"

  check_node

  if [ ! -d "${frontend_dir}/node_modules" ]; then
    echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
    cd "$frontend_dir"
    npm install
    cd "$ROOT_DIR"
  fi

  echo -e "${CYAN}🌐 Starting Frontend (port 3000, hot reload)...${NC}"
  cd "$frontend_dir"
  npm run dev &
  LOCAL_PIDS+=($!)
  echo -e "  ${GREEN}✓ PID $!${NC}"
  cd "$ROOT_DIR"
}

# ─── Cleanup handler ─────────────────────────────────────────────────────────

cleanup_local() {
  echo ""
  echo -e "${YELLOW}🛑 Shutting down local services...${NC}"
  for pid in "${LOCAL_PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo -e "  Stopped PID $pid"
    fi
  done
  echo -e "${GREEN}✓ All local services stopped${NC}"
  exit 0
}

# ─── Dev Commands ─────────────────────────────────────────────────────────────

cmd_dev() {
  echo -e "${BLUE}🚀 Starting AutoBGV in LOCAL DEV mode (live reload)...${NC}"
  echo ""

  # Start infra in Docker (only infra, not app services)
  check_docker
  echo -e "${CYAN}🐳 Starting infrastructure (Docker)...${NC}"
  docker compose -f "$COMPOSE_INFRA" up -d
  wait_for_infra
  echo ""

  # Set up trap for cleanup
  trap cleanup_local INT TERM

  # Start backend services locally
  start_workflow_local
  echo ""
  start_agent_local
  echo ""
  start_verification_local
  echo ""

  # Small wait for services to boot
  sleep 2

  # Start frontend locally
  start_frontend_local
  echo ""

  echo -e "${GREEN}✅ All services started in LOCAL DEV mode!${NC}"
  echo ""
  echo -e "  🌐 Frontend          → ${YELLOW}http://localhost:3000${NC}  (hot reload)"
  echo -e "  ⚙️  Workflow Service  → ${YELLOW}http://localhost:8001${NC}  (live reload)"
  echo -e "  🤖 Agent Service     → ${YELLOW}http://localhost:8002${NC}  (live reload)"
  echo -e "  ✅ Verify Service    → ${YELLOW}http://localhost:8003${NC}  (live reload)"
  echo -e "  📦 PostgreSQL        → ${YELLOW}localhost:5432${NC}          (Docker)"
  echo -e "  🔴 Redis             → ${YELLOW}localhost:6379${NC}          (Docker)"
  echo -e "  🗄️  MinIO            → ${YELLOW}http://localhost:9001${NC}  (Docker)"
  echo ""
  echo -e "  📚 API Docs:"
  echo -e "     Workflow Service  → ${YELLOW}http://localhost:8001/docs${NC}"
  echo -e "     Agent Service     → ${YELLOW}http://localhost:8002/docs${NC}"
  echo -e "     Verify Service    → ${YELLOW}http://localhost:8003/docs${NC}"
  echo ""
  echo -e "  ${YELLOW}Press Ctrl+C to stop all services${NC}"
  echo ""

  # Wait for all background processes
  wait
}

cmd_dev_setup() {
  echo -e "${BLUE}🔧 Setting up local development environment...${NC}"
  echo ""
  load_env
  setup_all_venvs
  echo ""
  check_node
  echo -e "${CYAN}📦 Installing frontend dependencies...${NC}"
  cd "${ROOT_DIR}/frontend"
  npm install
  cd "$ROOT_DIR"
  echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
  echo ""
  echo -e "${GREEN}✅ Dev setup complete! Run ${YELLOW}./start.sh dev${GREEN} to start.${NC}"
}

cmd_dev_workflow() {
  echo -e "${BLUE}🚀 Starting Workflow Service locally (live reload)...${NC}"
  load_env
  trap cleanup_local INT TERM
  start_workflow_local
  echo ""
  echo -e "${GREEN}✓ Workflow Service running at ${YELLOW}http://localhost:8001/docs${NC}"
  echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
  wait
}

cmd_dev_agent() {
  echo -e "${BLUE}🚀 Starting Agent Service locally (live reload)...${NC}"
  load_env
  trap cleanup_local INT TERM
  start_agent_local
  echo ""
  echo -e "${GREEN}✓ Agent Service running at ${YELLOW}http://localhost:8002/docs${NC}"
  echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
  wait
}

cmd_dev_verification() {
  echo -e "${BLUE}🚀 Starting Verification Service locally (live reload)...${NC}"
  load_env
  trap cleanup_local INT TERM
  start_verification_local
  echo ""
  echo -e "${GREEN}✓ Verification Service running at ${YELLOW}http://localhost:8003/docs${NC}"
  echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
  wait
}

cmd_dev_frontend() {
  echo -e "${BLUE}🚀 Starting Frontend locally (hot reload)...${NC}"
  load_env
  trap cleanup_local INT TERM
  start_frontend_local
  echo ""
  echo -e "${GREEN}✓ Frontend running at ${YELLOW}http://localhost:3000${NC}"
  echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
  wait
}

# ─── Docker Commands ──────────────────────────────────────────────────────────

cmd_infra() {
  echo -e "${BLUE}🚀 Starting infrastructure services...${NC}"
  docker compose -f "$COMPOSE_INFRA" up -d
  wait_for_infra
  echo -e "${GREEN}✓ Infrastructure started successfully!${NC}"
  echo ""
  echo -e "  📦 PostgreSQL  → ${YELLOW}localhost:5432${NC}"
  echo -e "  🔴 Redis       → ${YELLOW}localhost:6379${NC}"
  echo -e "  🗄️  MinIO       → ${YELLOW}localhost:9000${NC} (Console: localhost:9001)"
  echo ""
}

cmd_up() {
  echo -e "${BLUE}🚀 Starting all AutoBGV services (Docker)...${NC}"

  # Start infra first
  docker compose -f "$COMPOSE_INFRA" up -d
  wait_for_infra

  # Run migrations
  echo -e "${YELLOW}⚙️  Running database migrations...${NC}"
  docker compose -f "$COMPOSE_INFRA" -f "$COMPOSE_SERVICES" run --rm workflow-service alembic upgrade head 2>/dev/null || \
    echo -e "${YELLOW}⚠ Migration skipped (service not built yet or already up to date)${NC}"

  # Start application services
  docker compose -f "$COMPOSE_INFRA" -f "$COMPOSE_SERVICES" up -d

  echo ""
  echo -e "${GREEN}✓ All services started successfully!${NC}"
  echo ""
  echo -e "  🌐 Frontend          → ${YELLOW}http://localhost:3000${NC}"
  echo -e "  ⚙️  Workflow Service  → ${YELLOW}http://localhost:8001${NC}"
  echo -e "  🤖 Agent Service     → ${YELLOW}http://localhost:8002${NC}"
  echo -e "  ✅ Verify Service    → ${YELLOW}http://localhost:8003${NC}"
  echo -e "  📦 PostgreSQL        → ${YELLOW}localhost:5432${NC}"
  echo -e "  🔴 Redis             → ${YELLOW}localhost:6379${NC}"
  echo -e "  🗄️  MinIO            → ${YELLOW}http://localhost:9001${NC}"
  echo ""
  echo -e "  📚 API Docs:"
  echo -e "     Workflow Service  → ${YELLOW}http://localhost:8001/docs${NC}"
  echo -e "     Agent Service     → ${YELLOW}http://localhost:8002/docs${NC}"
  echo -e "     Verify Service    → ${YELLOW}http://localhost:8003/docs${NC}"
  echo ""
}

cmd_down() {
  echo -e "${YELLOW}🛑 Stopping all AutoBGV services...${NC}"
  docker compose -f "$COMPOSE_INFRA" -f "$COMPOSE_SERVICES" down
  echo -e "${GREEN}✓ All services stopped${NC}"
}

cmd_down_infra() {
  echo -e "${YELLOW}🛑 Stopping infrastructure services...${NC}"
  docker compose -f "$COMPOSE_INFRA" down
  echo -e "${GREEN}✓ Infrastructure stopped${NC}"
}

cmd_restart() {
  echo -e "${YELLOW}🔄 Restarting all services...${NC}"
  docker compose -f "$COMPOSE_INFRA" -f "$COMPOSE_SERVICES" restart
  echo -e "${GREEN}✓ Services restarted${NC}"
}

cmd_logs() {
  local service=$1
  if [ -n "$service" ]; then
    echo -e "${BLUE}📋 Logs for ${service}...${NC}"
    docker compose -f "$COMPOSE_INFRA" -f "$COMPOSE_SERVICES" logs -f "$service"
  else
    echo -e "${BLUE}📋 Logs for all services...${NC}"
    docker compose -f "$COMPOSE_INFRA" -f "$COMPOSE_SERVICES" logs -f
  fi
}

cmd_status() {
  echo -e "${BLUE}📊 Service Status:${NC}"
  echo ""
  docker compose -f "$COMPOSE_INFRA" -f "$COMPOSE_SERVICES" ps
}

cmd_build() {
  echo -e "${BLUE}🔨 Building all service images...${NC}"
  docker compose -f "$COMPOSE_SERVICES" build
  echo -e "${GREEN}✓ Build complete${NC}"
}

cmd_migrate() {
  echo -e "${YELLOW}⚙️  Running database migrations...${NC}"
  docker compose -f "$COMPOSE_INFRA" -f "$COMPOSE_SERVICES" run --rm workflow-service alembic upgrade head
  echo -e "${GREEN}✓ Migrations complete${NC}"
}

cmd_clean() {
  echo -e "${RED}⚠️  WARNING: This will remove all containers, volumes, and networks!${NC}"
  read -p "Are you sure? (y/N): " confirm
  if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    echo -e "${YELLOW}🗑️  Cleaning up...${NC}"
    docker compose -f "$COMPOSE_INFRA" -f "$COMPOSE_SERVICES" down -v --remove-orphans
    echo -e "${GREEN}✓ Cleanup complete${NC}"
  else
    echo -e "${YELLOW}Cleanup cancelled${NC}"
  fi
}

# ─── Main ─────────────────────────────────────────────────────────────────────

print_banner
load_env

case "$1" in
  # ─── Dev (local) ──────────────────────────────────────────────────────────
  dev)
    check_docker
    cmd_dev
    ;;
  dev:setup)
    cmd_dev_setup
    ;;
  dev:workflow)
    cmd_dev_workflow
    ;;
  dev:agent)
    cmd_dev_agent
    ;;
  dev:verification)
    cmd_dev_verification
    ;;
  dev:frontend)
    cmd_dev_frontend
    ;;
  # ─── Docker ───────────────────────────────────────────────────────────────
  infra)
    check_docker
    cmd_infra
    ;;
  up)
    check_docker
    cmd_up
    ;;
  down)
    check_docker
    cmd_down
    ;;
  down:infra)
    check_docker
    cmd_down_infra
    ;;
  restart)
    check_docker
    cmd_restart
    ;;
  logs)
    check_docker
    cmd_logs "$2"
    ;;
  status)
    check_docker
    cmd_status
    ;;
  build)
    check_docker
    cmd_build
    ;;
  migrate)
    check_docker
    cmd_migrate
    ;;
  clean)
    check_docker
    cmd_clean
    ;;
  *)
    print_usage
    exit 1
    ;;
esac
