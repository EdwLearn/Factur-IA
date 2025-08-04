"""
Document processing endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import uuid
import logging
import boto3
from datetime import datetime
import json

from ...config.settings import settings
from ...services.document_processor import DocumentProcessorService
from ...models.document import DocumentCreate, DocumentResponse, ProcessingStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
document_service = DocumentProcessorService()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF document to process")
):
    """
    Upload a PDF document for processing
    
    Args:
        file: PDF file to process
        
    Returns:
        Document information with processing job ID
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
        
        # Validate file size (10MB limit)
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size must be less than 10MB"
            )
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Read file content
        file_content = await file.read()
        
        # Upload to S3 and start processing
        result = await document_service.upload_and_process(
            document_id=document_id,
            filename=file.filename,
            file_content=file_content
        )
        
        logger.info(f"Document uploaded successfully: {document_id}")
        
        return DocumentResponse(
            document_id=document_id,
            filename=file.filename,
            status=ProcessingStatus.UPLOADED,
            upload_timestamp=datetime.utcnow(),
            s3_key=result["s3_key"],
            message="Document uploaded successfully and processing started"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {str(e)}"
        )

@router.get("/{document_id}/status", response_model=DocumentResponse)
async def get_document_status(document_id: str):
    """
    Get the processing status of a document
    
    Args:
        document_id: Unique document identifier
        
    Returns:
        Current processing status and details
    """
    try:
        status_info = await document_service.get_processing_status(document_id)
        
        if not status_info:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        
        return DocumentResponse(**status_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get document status: {str(e)}"
        )

@router.get("/{document_id}/results")
async def get_document_results(document_id: str):
    """
    Get the processing results of a document
    
    Args:
        document_id: Unique document identifier
        
    Returns:
        Extracted data and processing results
    """
    try:
        results = await document_service.get_processing_results(document_id)
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail="Document or results not found"
            )
        
        return {
            "document_id": document_id,
            "status": "completed",
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document results: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get document results: {str(e)}"
        )

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    limit: int = 10,
    offset: int = 0,
    status: Optional[ProcessingStatus] = None
):
    """
    List processed documents
    
    Args:
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        status: Filter by processing status
        
    Returns:
        List of documents with their status
    """
    try:
        documents = await document_service.list_documents(
            limit=limit,
            offset=offset,
            status=status
        )
        
        return documents
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}"
        )

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and its processing results
    
    Args:
        document_id: Unique document identifier
        
    Returns:
        Deletion confirmation
    """
    try:
        success = await document_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        
        return {
            "message": "Document deleted successfully",
            "document_id": document_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )