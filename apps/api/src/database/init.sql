-- Initial database setup for document processing
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size BIGINT,
    content_type VARCHAR(100) DEFAULT 'application/pdf',
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded',
    s3_key TEXT,
    upload_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_started TIMESTAMP WITH TIME ZONE,
    processing_completed TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create processing_results table
CREATE TABLE IF NOT EXISTS processing_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    total_pages INTEGER,
    extracted_text TEXT,
    textract_data JSONB,
    extracted_tables JSONB,
    extracted_forms JSONB,
    extracted_signatures JSONB,
    confidence_scores JSONB,
    processing_time_seconds FLOAT,
    textract_job_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_upload_timestamp ON documents(upload_timestamp);
CREATE INDEX IF NOT EXISTS idx_documents_s3_key ON documents(s3_key);
CREATE INDEX IF NOT EXISTS idx_processing_results_document_id ON processing_results(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_results_textract_data ON processing_results USING GIN (textract_data);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_processing_results_updated_at BEFORE UPDATE ON processing_results 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
