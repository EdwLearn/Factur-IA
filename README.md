# 🚀 AWS Document Processing System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![AWS](https://img.shields.io/badge/AWS-Lambda%20%7C%20Textract%20%7C%20S3-orange.svg)](https://aws.amazon.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://docker.com)
[![CDK](https://img.shields.io/badge/AWS%20CDK-Infrastructure-yellow.svg)](https://aws.amazon.com/cdk/)

> **Intelligent document processing system using AWS services for PDF analysis, text extraction, and automated data validation.**

## 🎯 Overview

This system processes multi-page PDF documents, converts them to images, extracts structured data using Amazon Textract, and validates business rules through machine learning models. Perfect for automating document workflows in enterprise environments.

## ✨ Features

### 🔄 **Document Processing Pipeline**
- **PDF to Image Conversion** - High-resolution conversion for optimal OCR
- **Amazon Textract Integration** - Extract text, tables, forms, and signatures
- **Amazon Comprehend** - Custom classification for relevant page detection
- **Amazon SageMaker** - Handwriting analysis and business rule validation

### 🌐 **API Endpoints**
- **POST** `/api/v1/documents/upload` - Upload PDF documents
- **GET** `/api/v1/documents/{id}/status` - Check processing status
- **GET** `/api/v1/documents/{id}/results` - Retrieve extraction results
- **GET** `/api/v1/documents/` - List all processed documents
- **DELETE** `/api/v1/documents/{id}` - Remove documents

### 🏗️ **Serverless Architecture**
- **AWS Lambda Functions** - Scalable, event-driven processing
- **Step Functions** - Orchestrated workflows with error handling
- **S3 Storage** - Secure document and result storage
- **FastAPI** - Modern, async REST API framework

## 🛠️ Tech Stack

### **AWS Services**
- **Compute**: Lambda, Fargate, SageMaker
- **Storage**: S3, RDS (MySQL), DynamoDB
- **AI/ML**: Textract, Comprehend, SageMaker, Rekognition
- **Orchestration**: Step Functions
- **Monitoring**: CloudWatch, X-Ray

### **Python Ecosystem**
```python
# Core Dependencies
boto3>=1.34.34          # AWS SDK
fastapi>=0.109.0        # Modern API framework
pandas>=2.2.0           # Data manipulation
sqlalchemy>=2.0.25      # Database ORM
pydantic>=2.5.3         # Data validation

# Document Processing
pdf2image>=1.17.0       # PDF conversion
PyMuPDF>=1.23.14       # PDF manipulation
pillow>=10.2.0          # Image processing
🚀 Quick Start
```

## Prerequisites

Python 3.10+
AWS CLI configured
Docker & Docker Compose
Node.js (for AWS CDK)

### Installation
```bash
# Clone repository
git clone https://github.com/EdwLearn/aws-document-processing.git
cd aws-document-processing

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your AWS credentials

# Start API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```
API Documentation
Once running, access:

API Docs: http://localhost:8000/docs
Health Check: http://localhost:8000/health
API Root: http://localhost:8000/


📁 Project Structure
```
aws-document-processing/
├── 🏗️ infrastructure/
│   ├── cdk/                    # AWS CDK stacks
│   └── terraform/              # Alternative IaC
├── 🐍 src/
│   ├── lambda_functions/       # Serverless functions
│   │   └── document_processor/ # PDF processing Lambda
│   ├── api/                    # FastAPI application
│   │   ├── main.py            # API entry point
│   │   └── routers/           # Route handlers
│   ├── models/                 # Pydantic data models
│   ├── services/               # Business logic
│   ├── config/                 # Settings management
│   └── utils/                  # Helper functions
├── 🧪 tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test data
├── 📊 notebooks/               # Jupyter notebooks
├── 🔧 scripts/                 # Automation scripts
└── 📚 docs/                    # Documentation
```

# 🎯 Current Status
✅ Completed Features

 Document Processor Lambda - PDF to images + Textract integration
 FastAPI Application - Complete REST API with async endpoints
 Project Structure - Scalable architecture with best practices
 Unit Testing - Comprehensive test suite with mocks
 Development Environment - Docker, testing, and local development

🚧 In Progress

 S3 Integration - Real file upload and storage
 CDK Infrastructure - AWS resources deployment
 Step Functions - Workflow orchestration
 Database Integration - Persistent data storage

📋 Roadmap

 SageMaker Integration - Handwriting analysis model
 Comprehend Classification - Page relevance detection
 ANI API Integration - Identity validation
 QuickSight Dashboards - Business intelligence
 Production Deployment - Multi-environment setup

🧪 Testing
```bash
Run all tests
pytest

# Run specific test file
pytest tests/unit/test_document_processor.py -v
pytest tests/unit/test_api.py -v

# Run with coverage
pytest --cov=src tests/

# Integration tests (requires AWS credentials)
pytest tests/integration/ -v
```

📊 API Usage Examples


```bash
# Upload Document
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@document.pdf"
     
#Check Status
curl "http://localhost:8000/api/v1/documents/{document_id}/status"

# Get Results
curl "http://localhost:8000/api/v1/documents/{document_id}/results"
```

🏛️ Architecture Principles

Serverless-First - Pay only for what you use
Event-Driven - Reactive processing pipeline
Microservices - Single responsibility functions
API-First - Well-documented, testable endpoints
Infrastructure as Code - Reproducible deployments

🤝 Contributing

Fork the repository
```
Create a feature branch: git checkout -b feature/amazing-feature
Commit changes: git commit -m 'Add amazing feature'
Push to branch: git push origin feature/amazing-feature
Open a Pull Request
```

🙏 Acknowledgments

AWS for providing excellent cloud services
FastAPI for the modern Python web framework
Open source community for amazing packages


<div align="center">
Built with ❤️ using AWS and Python
⭐ Star this repo • 🐛 Report Bug • ✨ Request Feature
</div>
