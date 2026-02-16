.PHONY: test lint format clean docker-up docker-down

# Run all tests with coverage
test:
	pytest --cov=app --cov-report=term-missing -v tests/

# Run linting checks
lint:
	black --check .
	isort --check .
	flake8

# Auto-format code
format:
	black .
	isort .

# Remove build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage coverage.xml

# Start services
docker-up:
	docker-compose up -d --build

# Stop services
docker-down:
	docker-compose down
