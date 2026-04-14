#!/bin/bash
set -e

echo "☁️  Initializing LocalStack..."

# Wait for LocalStack to be ready
for i in {1..30}; do
    if awslocal s3 ls &> /dev/null; then
        echo "✅ LocalStack is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ LocalStack did not become ready"
        exit 1
    fi
    sleep 2
done

# Create S3 buckets
echo "📦 Creating S3 buckets..."
awslocal s3 mb s3://facturia-test-documents 2>/dev/null || echo "Bucket facturia-test-documents already exists"
awslocal s3 mb s3://facturia-test-results 2>/dev/null || echo "Bucket facturia-test-results already exists"

# Set CORS configuration for buckets
echo "🔧 Configuring CORS..."
awslocal s3api put-bucket-cors --bucket facturia-test-documents --cors-configuration '{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}'

# Enable public access for testing
echo "🔓 Enabling public access..."
awslocal s3api put-bucket-acl --bucket facturia-test-documents --acl public-read

echo "✅ LocalStack initialization completed"
