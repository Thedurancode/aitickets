.PHONY: help dev api mcp test lint format clean install docker-build docker-up docker-down migrate

help:
	@echo "Available commands:"
	@echo "  make dev          - Run both API and MCP servers concurrently"
	@echo "  make api          - Run FastAPI server only"
	@echo "  make mcp          - Run MCP server only"
	@echo "  make test         - Run pytest tests"
	@echo "  make lint         - Run ruff linter"
	@echo "  make format       - Format code with ruff"
	@echo "  make clean        - Clean up cache and build files"
	@echo "  make install      - Install dependencies"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start services with docker-compose"
	@echo "  make docker-down  - Stop docker-compose services"
	@echo "  make migrate      - Run database migrations"

dev:
	@echo "Starting API and MCP servers..."
	@uvicorn app.main:app --reload --port 8000 & \
	python -m mcp_server.http_server --port 3001

api:
	@echo "Starting FastAPI server on http://localhost:8000"
	@uvicorn app.main:app --reload --port 8000

mcp:
	@echo "Starting MCP server on http://localhost:3001"
	@python -m mcp_server.http_server --port 3001

test:
	@echo "Running tests..."
	@pytest tests/ -v --tb=short

test-cov:
	@echo "Running tests with coverage..."
	@pytest tests/ -v --cov=app --cov-report=html --cov-report=term

lint:
	@echo "Running ruff linter..."
	@ruff check app/ mcp_server/ tests/

format:
	@echo "Formatting code with ruff..."
	@ruff check --fix app/ mcp_server/ tests/
	@ruff format app/ mcp_server/ tests/

clean:
	@echo "Cleaning up cache and build files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@rm -f .coverage
	@echo "Cleanup complete!"

install:
	@echo "Installing dependencies..."
	@pip install -r requirements.txt

install-dev:
	@echo "Installing dependencies with dev tools..."
	@pip install -r requirements.txt
	@pip install ruff pytest-cov pre-commit

migrate:
	@echo "Running database migrations..."
	@python -c "from app.database import init_db; init_db()"

docker-build:
	@echo "Building Docker image..."
	@docker build -t ai-tickets .

docker-up:
	@echo "Starting Docker services..."
	@docker-compose up -d

docker-down:
	@echo "Stopping Docker services..."
	@docker-compose down

fly-deploy:
	@echo "Deploying to Fly.io..."
	@fly deploy --remote-only

fly-logs:
	@echo "Tailing Fly.io logs..."
	@fly logs

health:
	@echo "Checking health endpoint..."
	@curl -s http://localhost:8000/health | python -m json.tool
