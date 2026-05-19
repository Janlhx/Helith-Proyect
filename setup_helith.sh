#!/bin/bash
# Helith - Project Structure Setup
# Run this from the root of your cloned repo

set -e

echo "🚀 Setting up Helith project structure..."

# GitHub Actions
mkdir -p .github/workflows
touch .github/workflows/ci.yml
touch .github/workflows/cd.yml

# Core
mkdir -p core/db
mkdir -p core/llm
touch core/__init__.py
touch core/db/__init__.py
touch core/db/connection.py
touch core/db/fallback.py
touch core/llm/__init__.py
touch core/llm/pool.py
touch core/llm/fallback.py
touch core/config.py
touch core/exceptions.py

# Domains
for domain in bot conversation osu monitoring admin; do
  mkdir -p domains/$domain
  touch domains/$domain/__init__.py
  touch domains/$domain/models.py
  touch domains/$domain/repository.py
  touch domains/$domain/service.py
  touch domains/$domain/router.py
done

# Tests
mkdir -p tests/unit
mkdir -p tests/integration
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

# Docs
mkdir -p docs
touch docs/architecture.md
touch docs/contributing.md

# Root files
touch .env.example
touch docker-compose.yml
touch pyproject.toml

echo ""
echo "✅ Structure created successfully!"
echo ""
echo "Next steps:"
echo "  1. cd into your repo folder"
echo "  2. Run: bash setup_helith.sh"
echo "  3. git add . && git commit -m 'chore: initialize project structure'"
echo "  4. git push origin development"
