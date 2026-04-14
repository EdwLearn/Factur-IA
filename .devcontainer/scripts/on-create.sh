#!/bin/bash
set -e

echo "📦 Installing dependencies..."

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies..."
    pip install --no-cache-dir -r requirements.txt
    echo "✅ Python dependencies installed"
fi

# Install API-specific dependencies
if [ -f "apps/api/pyproject.toml" ]; then
    echo "📦 Installing API dependencies..."
    pip install --no-cache-dir -e apps/api/
    echo "✅ API dependencies installed"
fi

# Install Node.js dependencies
if [ -f "pnpm-workspace.yaml" ]; then
    echo "📦 Installing Node.js dependencies with pnpm..."
    pnpm install --frozen-lockfile
    echo "✅ Node.js dependencies installed"
elif [ -f "package.json" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
    echo "✅ Node.js dependencies installed"
fi

# Install Playwright browsers
if [ -d "apps/web" ]; then
    echo "🎭 Installing Playwright browsers..."
    cd apps/web && pnpm exec playwright install --with-deps chromium && cd ../..
    echo "✅ Playwright browsers installed"
fi

# Setup git hooks if pre-commit is available
if command -v pre-commit &> /dev/null; then
    echo "🪝 Setting up git hooks..."
    pre-commit install
    echo "✅ Git hooks installed"
fi

# Make test scripts executable
echo "🔧 Making test scripts executable..."
chmod +x scripts/*.sh 2>/dev/null || true
chmod +x .devcontainer/scripts/*.sh 2>/dev/null || true
echo "✅ Scripts are executable"

# Create necessary directories
mkdir -p apps/api/htmlcov
mkdir -p apps/web/coverage
mkdir -p apps/web/playwright-report
mkdir -p apps/web/test-results

echo "✅ Container setup completed successfully"
