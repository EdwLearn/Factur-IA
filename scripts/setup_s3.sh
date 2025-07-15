#!/bin/bash

echo "🪣 Creating S3 bucket for Textract..."

# Create S3 bucket for development
aws s3 mb s3://invoice-saas-textract-dev --region us-east-1

# Set bucket policy for Textract access
aws s3api put-bucket-policy --bucket invoice-saas-textract-dev --policy '{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "TextractAccess",
            "Effect": "Allow",
            "Principal": {
                "Service": "textract.amazonaws.com"
            },
            "Action": [
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::invoice-saas-textract-dev/*"
        }
    ]
}'

echo "✅ S3 bucket ready for Textract"
