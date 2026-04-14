#!/bin/bash
set -e

echo "🔄 Updating dependencies..."

# Update Python dependencies
if [ -f "requirements.txt" ]; then
    echo "🔄 Updating Python dependencies..."
    pip install --no-cache-dir --upgrade -r requirements.txt
    echo "✅ Python dependencies updated"
fi

# Update Node.js dependencies
if [ -f "pnpm-workspace.yaml" ]; then
    echo "🔄 Updating Node.js dependencies..."
    pnpm update
    echo "✅ Node.js dependencies updated"
elif [ -f "package.json" ]; then
    echo "🔄 Updating Node.js dependencies..."
    npm update
    echo "✅ Node.js dependencies updated"
fi

# Update Playwright browsers
if command -v playwright &> /dev/null; then
    echo "🎭 Updating Playwright browsers..."
    cd apps/web && pnpm exec playwright install --with-deps chromium && cd ../..
    echo "✅ Playwright browsers updated"
fi

echo "✅ All dependencies updated successfully"
