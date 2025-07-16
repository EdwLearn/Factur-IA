"""
Test script for image enhancement with real invoice photos
"""
import os
import sys
import logging
from pathlib import Path

# Add project root to path (go up 3 levels from current test file)
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.document_processing.computer_vision import DocumentImageEnhancer, ImageToPDFConverter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_image_enhancement(input_image_path: str, output_dir: str = "test_outputs"):
    """Test the complete image enhancement pipeline"""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize services
    enhancer = DocumentImageEnhancer()
    pdf_converter = ImageToPDFConverter()
    
    print(f"🔍 Testing image enhancement with: {input_image_path}")
    
    try:
        # 1. Read the input image
        with open(input_image_path, 'rb') as f:
            original_image_bytes = f.read()
        
        print(f"📂 Original image size: {len(original_image_bytes)} bytes")
        
        # 2. Enhance the image
        print("🔧 Enhancing image...")
        enhanced_image_bytes = enhancer.enhance_invoice_photo(original_image_bytes)
        
        print(f"✨ Enhanced image size: {len(enhanced_image_bytes)} bytes")
        
        # 3. Save enhanced image for comparison
        enhanced_image_path = os.path.join(output_dir, "enhanced_image.jpg")
        with open(enhanced_image_path, 'wb') as f:
            f.write(enhanced_image_bytes)
        
        print(f"💾 Enhanced image saved: {enhanced_image_path}")
        
        # 4. Convert to PDF
        print("📄 Converting to PDF...")
        pdf_bytes = pdf_converter.convert_to_pdf(enhanced_image_bytes)
        
        print(f"📋 PDF size: {len(pdf_bytes)} bytes")
        
        # 5. Save PDF
        pdf_path = os.path.join(output_dir, "enhanced_invoice.pdf")
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"💾 PDF saved: {pdf_path}")
        
        # 6. Validate PDF for Textract
        is_valid = pdf_converter.validate_pdf_for_textract(pdf_bytes)
        print(f"✅ PDF Textract validation: {'PASSED' if is_valid else 'FAILED'}")
        
        print("\n🎉 Test completed successfully!")
        print(f"📁 Check outputs in: {output_dir}/")
        print(f"   - Original: {input_image_path}")
        print(f"   - Enhanced: {enhanced_image_path}")
        print(f"   - PDF: {pdf_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🧪 Image Enhancement Testing Tool")
    print("=" * 50)
    
    # Check if image path provided
    if len(sys.argv) < 2:
        print("Usage: python test_image_enhancement.py <path_to_image>")
        print("\nExample:")
        print("  python test_image_enhancement.py invoice_photo.jpg")
        print("  python test_image_enhancement.py /path/to/your/invoice.png")
        return
    
    input_image = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(input_image):
        print(f"❌ File not found: {input_image}")
        return
    
    # Run the test
    success = test_image_enhancement(input_image)
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Test failed!")

if __name__ == "__main__":
    main()
