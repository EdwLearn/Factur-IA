"""
Convert enhanced images to PDF for Textract processing
"""
import img2pdf
import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

class ImageToPDFConverter:
    """Convert enhanced images to PDF format for Textract"""
    
    def __init__(self):
        # PDF settings optimized for Textract
        self.dpi = 200  # Good balance for Textract
        self.quality = 85  # JPEG quality
    
    def convert_to_pdf(self, image_bytes: bytes, filename: str = "enhanced_invoice.pdf") -> bytes:
        """
        Convert enhanced image to PDF
        
        Args:
            image_bytes: Enhanced image bytes
            filename: Output filename (for metadata)
            
        Returns:
            PDF bytes ready for Textract
        """
        try:
            # Convert to PIL Image for validation
            img = Image.open(io.BytesIO(image_bytes))
            
            # Ensure RGB mode (img2pdf requirement)
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
                # Convert back to bytes
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=self.quality, dpi=(self.dpi, self.dpi))
                image_bytes = img_buffer.getvalue()
            
            # Convert to PDF
            pdf_bytes = img2pdf.convert(image_bytes)
            
            logger.info(f"Successfully converted image to PDF: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error converting image to PDF: {str(e)}")
            raise
    
    def validate_pdf_for_textract(self, pdf_bytes: bytes) -> bool:
        """Validate PDF meets Textract requirements"""
        try:
            # Basic size validation (Textract limit: 5MB for synchronous, 500MB for async)
            size_mb = len(pdf_bytes) / (1024 * 1024)
            
            if size_mb > 5:
                logger.warning(f"PDF size {size_mb:.2f}MB exceeds Textract sync limit")
                return False
            
            if size_mb > 500:
                logger.error(f"PDF size {size_mb:.2f}MB exceeds Textract limits")
                return False
            
            logger.info(f"PDF validation passed: {size_mb:.2f}MB")
            return True
            
        except Exception as e:
            logger.error(f"Error validating PDF: {str(e)}")
            return False
