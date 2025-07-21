# NETCONF Memory Leak Analyzer - Makefile

.PHONY: help install test lint format clean build docker run docs

# Default target
help:
	@echo "🔬 NETCONF Memory Leak Analyzer - Available Commands:"
	@echo ""
	@echo "📦 Setup:"
	@echo "  install      Install dependencies and setup development environment"
	@echo "  install-dev  Install with development dependencies"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test         Run all tests"
	@echo "  test-unit    Run unit tests only"
	@echo "  test-cov     Run tests with coverage report"
	@echo "  test-device  Run device integration tests (requires config)"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black"
	@echo "  type-check   Run type checking with mypy"
	@echo "  security     Run security checks"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  docker-build Build Docker image"
	@echo "  docker-run   Run in Docker container"
	@echo "  docker-dev   Run development environment with Docker Compose"
	@echo ""
	@echo "📚 Documentation:"
	@echo "  docs         Build documentation"
	@echo "  docs-serve   Serve documentation locally"
	@echo ""
	@echo "🚀 Deployment:"
	@echo "  build        Build distribution packages"
	@echo "  release      Create a new release"
	@echo "  clean        Clean build artifacts"

# Setup and Installation
install:
	pip install -r requirements.txt
	pip install -e .

install-dev:
	pip install -r requirements.txt
	pip install -e ".[dev,gui,plotting,docs]"
	pre-commit install

# Testing
test:
	pytest

test-unit:
	pytest tests/unit/

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

test-device:
	@echo "🔧 Running device integration tests..."
	@echo "📝 Make sure you have a valid test_device_config.yaml"
	python -m pytest tests/integration/ -v

# Code Quality
lint:
	flake8 src/ tests/ *.py
	bandit -r src/

format:
	black src/ tests/ *.py
	isort src/ tests/ *.py

type-check:
	mypy src/ --ignore-missing-imports

security:
	bandit -r src/
	safety check

# Docker
docker-build:
	docker build -t netconf-memory-analyzer:latest .

docker-run:
	docker run -it --rm \
		-v $(PWD)/results:/app/results \
		-v $(PWD)/config:/app/config \
		netconf-memory-analyzer:latest

docker-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

docker-clean:
	docker-compose down
	docker image prune -f

# Documentation
docs:
	cd docs && make html

docs-serve:
	cd docs/_build/html && python -m http.server 8000

# Build and Release
build:
	python -m build

release: clean build
	python -m twine upload dist/*

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Development Shortcuts
dev-setup: install-dev
	@echo "🎉 Development environment setup complete!"
	@echo "📝 Next steps:"
	@echo "  1. Copy config/simple_device_config.yaml to config/dev_config.yaml"
	@echo "  2. Edit config/dev_config.yaml with your device details"
	@echo "  3. Run: make test-device"

quick-test: format lint test

full-check: format lint type-check security test-cov

# Utility targets
sample-data:
	python create_sample_rpcs.py test_data/dev_rpcs
	@echo "📁 Sample RPC files created in test_data/dev_rpcs/"

config-template:
	cp config/simple_device_config.yaml config/my_config.yaml
	@echo "📝 Configuration template created: config/my_config.yaml"
	@echo "🔧 Edit this file with your device details"

demo:
	@echo "🎬 Running demonstration..."
	python simulate_containerized_test.py
	@echo "✅ Demo complete! Check output_examples/ for results"

# CI/CD helpers
ci-install:
	pip install -r requirements.txt
	pip install pytest pytest-cov flake8 black bandit safety mypy

ci-test: ci-install
	make full-check

# Help for specific commands
install-help:
	@echo "📦 Installation Help:"
	@echo "  install      - Install basic dependencies for usage"
	@echo "  install-dev  - Install with development tools (recommended for contributors)"
	@echo "  dev-setup    - Complete development environment setup"

test-help:
	@echo "🧪 Testing Help:"
	@echo "  test         - Run all tests (unit + integration)"
	@echo "  test-unit    - Run only unit tests (fast, no devices needed)"
	@echo "  test-cov     - Run tests with HTML coverage report"
	@echo "  test-device  - Test with real devices (requires config/test_device_config.yaml)"

docker-help:
	@echo "🐳 Docker Help:"
	@echo "  docker-build - Build the Docker image"
	@echo "  docker-run   - Run analyzer in container"
	@echo "  docker-dev   - Development environment with hot reload" 