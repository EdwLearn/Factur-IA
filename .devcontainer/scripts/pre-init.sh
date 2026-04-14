#!/bin/bash
set -e

echo "🔧 Pre-initialization checks..."

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo "✅ Docker is available and running"

# Check Docker socket permissions
if [ -e "/var/run/docker.sock" ]; then
    echo "✅ Docker socket exists"
else
    echo "⚠️  Docker socket not found at /var/run/docker.sock"
fi

# Check available disk space (need at least 5GB)
available_space=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$available_space" -lt 5 ]; then
    echo "⚠️  Warning: Less than 5GB available disk space (${available_space}GB)"
else
    echo "✅ Sufficient disk space available (${available_space}GB)"
fi

# Create necessary directories if they don't exist
mkdir -p .devcontainer/test-data/{fixtures,sample-invoices}
mkdir -p .devcontainer/scripts

echo "✅ Pre-initialization completed successfully"
