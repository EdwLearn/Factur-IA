"""
Image enhancement service for mobile invoice photos
Optimizes photos for AWS Textract processing
"""
import cv2
import numpy as np
import logging
from typing import Tuple, Optional
from PIL import Image
import io

logger = logging.getLogger(__name__)

class DocumentImageEnhancer:
    """Enhance mobile photos of invoices for better Textract accuracy"""
    
    def __init__(self):
        # Optimal settings for invoice processing
        self.target_width = 1200  # Good balance for Textract
        self.target_height = 1600
        self.gaussian_blur_kernel = (5, 5)
        self.bilateral_filter_params = (9, 75, 75)
    
    def enhance_invoice_photo(self, image_bytes: bytes) -> bytes:
        """
        Main function to enhance mobile photo of invoice
        
        Args:
            image_bytes: Raw image bytes from mobile photo
            
        Returns:
            Enhanced image bytes ready for PDF conversion
        """
        try:
            # Convert bytes to OpenCV image
            img = self._bytes_to_cv2(image_bytes)
            
            logger.info(f"Original image shape: {img.shape}")
            
            # Step 1: Resize if too large (save processing time)
            img = self._resize_if_needed(img)
            
            # Step 2: Detect and straighten document
            img = self._detect_and_straighten_document(img)
            
            # Step 3: Enhance image quality
            img = self._enhance_quality(img)
            
            # Step 4: Final optimization for Textract
            img = self._optimize_for_textract(img)
            
            # Convert back to bytes
            enhanced_bytes = self._cv2_to_bytes(img)
            
            logger.info("Image enhancement completed successfully")
            return enhanced_bytes
            
        except Exception as e:
            logger.error(f"Error enhancing image: {str(e)}")
            # Return original image if enhancement fails
            return image_bytes
    
    def _bytes_to_cv2(self, image_bytes: bytes) -> np.ndarray:
        """Convert bytes to OpenCV image"""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Could not decode image")
        
        return img
    
    def _cv2_to_bytes(self, img: np.ndarray, format: str = '.jpg') -> bytes:
        """Convert OpenCV image to bytes"""
        is_success, buffer = cv2.imencode(format, img)
        
        if not is_success:
            raise ValueError("Could not encode image")
        
        return buffer.tobytes()
    
    def _resize_if_needed(self, img: np.ndarray) -> np.ndarray:
        """Resize image if it's too large (optimization)"""
        height, width = img.shape[:2]
        
        # If image is very large, resize to save processing time
        if width > 2400 or height > 3200:
            # Calculate scale factor
            scale_w = 2400 / width if width > 2400 else 1
            scale_h = 3200 / height if height > 3200 else 1
            scale = min(scale_w, scale_h)
            
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            logger.info(f"Resized image to: {new_width}x{new_height}")
        
        return img
    
    def _detect_and_straighten_document(self, img: np.ndarray) -> np.ndarray:
        """Detect document boundaries and apply perspective correction"""
        try:
            # Convert to grayscale for edge detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, self.gaussian_blur_kernel, 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Find the largest rectangular contour (likely the document)
            document_contour = self._find_document_contour(contours, img.shape)
            
            if document_contour is not None:
                # Apply perspective correction
                img = self._apply_perspective_correction(img, document_contour)
                logger.info("Applied perspective correction")
            else:
                logger.info("No document boundary detected, using original image")
            
            return img
            
        except Exception as e:
            logger.warning(f"Error in document detection: {str(e)}")
            return img
    
    def _find_document_contour(self, contours, img_shape) -> Optional[np.ndarray]:
        """Find the contour that most likely represents the document"""
        if not contours:
            return None
        
        height, width = img_shape[:2]
        min_area = (width * height) * 0.1  # Document should be at least 10% of image
        
        best_contour = None
        best_score = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if area < min_area:
                continue
            
            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # We want a quadrilateral (4 corners)
            if len(approx) == 4:
                # Calculate how "rectangular" this contour is
                score = area / (width * height)
                
                if score > best_score:
                    best_score = score
                    best_contour = approx
        
        return best_contour
    
    def _apply_perspective_correction(self, img: np.ndarray, contour: np.ndarray) -> np.ndarray:
        """Apply perspective correction based on detected document contour"""
        try:
            # Get the four corners of the document
            pts = contour.reshape(4, 2).astype(np.float32)
            
            # Order points: top-left, top-right, bottom-right, bottom-left
            pts = self._order_points(pts)
            
            # Calculate dimensions of the straightened document
            width = int(max(
                np.linalg.norm(pts[1] - pts[0]),  # top edge
                np.linalg.norm(pts[2] - pts[3])   # bottom edge
            ))
            
            height = int(max(
                np.linalg.norm(pts[3] - pts[0]),  # left edge
                np.linalg.norm(pts[2] - pts[1])   # right edge
            ))
            
            # Define destination points for perspective transform
            dst_pts = np.array([
                [0, 0],
                [width - 1, 0],
                [width - 1, height - 1],
                [0, height - 1]
            ], dtype=np.float32)
            
            # Calculate perspective transform matrix
            matrix = cv2.getPerspectiveTransform(pts, dst_pts)
            
            # Apply perspective transform
            corrected = cv2.warpPerspective(img, matrix, (width, height))
            
            return corrected
            
        except Exception as e:
            logger.warning(f"Error applying perspective correction: {str(e)}")
            return img
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Order points as: top-left, top-right, bottom-right, bottom-left"""
        # Sort by y-coordinate
        y_sorted = pts[np.argsort(pts[:, 1]), :]
        
        # Top two points
        top = y_sorted[:2, :]
        top = top[np.argsort(top[:, 0]), :]  # Sort by x
        top_left, top_right = top
        
        # Bottom two points  
        bottom = y_sorted[2:, :]
        bottom = bottom[np.argsort(bottom[:, 0]), :]  # Sort by x
        bottom_left, bottom_right = bottom
        
        return np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.float32)
    
    def _enhance_quality(self, img: np.ndarray) -> np.ndarray:
        """Enhance image quality for better OCR"""
        # Apply bilateral filter to reduce noise while keeping edges sharp
        enhanced = cv2.bilateralFilter(img, *self.bilateral_filter_params)
        
        # Convert to LAB color space for better contrast enhancement
        lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge channels and convert back to BGR
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        return enhanced
    
    def _optimize_for_textract(self, img: np.ndarray) -> np.ndarray:
        """Final optimizations specifically for AWS Textract"""
        # Resize to optimal dimensions for Textract
        height, width = img.shape[:2]
        
        # Textract works best with specific resolutions
        if width != self.target_width or height != self.target_height:
            # Maintain aspect ratio
            scale = min(self.target_width / width, self.target_height / height)
            
            if scale < 1:  # Only downscale, never upscale
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # Slight sharpening for text clarity
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        img = cv2.filter2D(img, -1, kernel)
        
        return img
