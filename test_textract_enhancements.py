#!/usr/bin/env python3
"""
Test script for Textract enhancements
Tests unit conversions and item/ref separation
"""

import sys
import os
from pathlib import Path
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.document_processing.textract.textract_enhancer import TextractDataEnhancer

def test_unit_conversions():
    """Test unit conversion functionality"""
    print("🔄 Testing Unit Conversions")
    print("=" * 50)
    
    enhancer = TextractDataEnhancer()
    
    # Test cases based on the Casoli invoice
    test_items = [
        {
            'product_code': '049 (DAMA)',
            'description': 'CHANCLA RAJADO DAMA 36-40 (X7)(8 BUENO)',
            'quantity': Decimal('1'),
            'unit_measure': 'DOC',
            'unit_price': Decimal('105000'),
            'subtotal': Decimal('105000')
        },
        {
            'product_code': '930-D',
            'description': 'CHANCLA RAJADO DAMA 36-40 (X6)(8 BUENO)',
            'quantity': Decimal('1'),
            'unit_measure': 'DOC',
            'unit_price': Decimal('98000'),
            'subtotal': Decimal('98000')
        },
        {
            'product_code': 'MINIMACK',
            'description': 'SANDALIA NIÑA 18-23 (X6)(WAY INT.)',
            'quantity': Decimal('2'),
            'unit_measure': 'PAR',
            'unit_price': Decimal('84000'),
            'subtotal': Decimal('168000')
        }
    ]
    
    print("📋 Original Items:")
    for i, item in enumerate(test_items, 1):
        print(f"  {i}. {item['product_code']} - {item['quantity']} {item['unit_measure']} @ ${item['unit_price']}")
    
    print("\n🔧 Processing conversions...")
    enhanced_items = enhancer._enhance_line_items(test_items)
    
    print("\n✨ Enhanced Items:")
    for i, item in enumerate(enhanced_items, 1):
        original_qty = item.get('original_quantity', 'N/A')
        original_unit = item.get('original_unit', 'N/A')
        current_qty = item.get('quantity', 'N/A')
        current_unit = item.get('unit_measure', 'N/A')
        multiplier = item.get('unit_multiplier', 1)
        
        print(f"  {i}. {item['product_code']}")
        print(f"     Original: {original_qty} {original_unit}")
        print(f"     Converted: {current_qty} {current_unit} (x{multiplier})")
        print(f"     Enhancement: {item.get('_enhancement_applied', 'none')}")
        print()
    
    return enhanced_items

def test_item_ref_separation():
    """Test item number and reference separation"""
    print("🔍 Testing Item/Reference Separation")
    print("=" * 50)
    
    enhancer = TextractDataEnhancer()
    
    # Test cases based on real OCR issues
    test_cases = [
        {
            'product_code': '1 049 (DAMA)',
            'description': 'CHANCLA RAJADO DAMA 36-40',
            'expected_item': 1,
            'expected_ref': '049 (DAMA)'
        },
        {
            'product_code': '2 930-D',
            'description': 'CHANCLA RAJADO DAMA 36-40',
            'expected_item': 2,
            'expected_ref': '930-D'
        },
        {
            'product_code': '8 MINIMACK',
            'description': 'SANDALIA NIÑA',
            'expected_item': 8,
            'expected_ref': 'MINIMACK'
        },
        {
            'product_code': '15. ABC-123',
            'description': 'Test product with dot separator',
            'expected_item': 15,
            'expected_ref': 'ABC-123'
        },
        {
            'product_code': 'CLEAN-REF',
            'description': 'Already clean reference',
            'expected_item': 5,
            'expected_ref': 'CLEAN-REF'
        }
    ]
    
    print("📋 Test Cases:")
    for i, case in enumerate(test_cases, 1):
        print(f"  {i}. '{case['product_code']}' → item={case['expected_item']}, ref='{case['expected_ref']}'")
    
    print("\n🔧 Processing separations...")
    
    results = []
    for i, case in enumerate(test_cases, 1):
        item = {
            'product_code': case['product_code'],
            'description': case['description']
        }
        
        enhanced_item = enhancer._separate_item_and_ref(item, case['expected_item'])
        
        actual_item = enhanced_item.get('item_number')
        actual_ref = enhanced_item.get('product_code')
        
        success = (actual_item == case['expected_item'] and 
                  actual_ref == case['expected_ref'])
        
        status = "✅" if success else "❌"
        
        results.append({
            'test_case': i,
            'original': case['product_code'],
            'expected_item': case['expected_item'],
            'expected_ref': case['expected_ref'],
            'actual_item': actual_item,
            'actual_ref': actual_ref,
            'success': success,
            'enhancement': enhanced_item.get('_enhancement_applied', 'none')
        })
        
        print(f"  {status} Test {i}: '{case['product_code']}'")
        print(f"     Expected: item={case['expected_item']}, ref='{case['expected_ref']}'")
        print(f"     Actual:   item={actual_item}, ref='{actual_ref}'")
        print(f"     Enhancement: {enhanced_item.get('_enhancement_applied', 'none')}")
        print()
    
    return results

def test_full_invoice_enhancement():
    """Test full invoice enhancement with Casoli data"""
    print("📄 Testing Full Invoice Enhancement")
    print("=" * 50)
    
    enhancer = TextractDataEnhancer()
    
    # Mock invoice data based on the Casoli invoice
    mock_invoice_data = {
        'invoice_number': 'JLU-32419',
        'supplier': {
            'company_name': 'DESPACHOS COMERCIALES MILTONCESAR DUERO HOYOS',
            'nit': '70353036'
        },
        'line_items': [
            {
                'product_code': '1 049 (DAMA)',
                'description': 'CHANCLA RAJADO DAMA 36-40 (X7)(8 BUENO)',
                'quantity': Decimal('1'),
                'unit_measure': 'DOC',
                'unit_price': Decimal('105000'),
                'subtotal': Decimal('105000')
            },
            {
                'product_code': '2 930-D',
                'description': 'CHANCLA RAJADO DAMA 36-40 (X6)(8 BUENO)',
                'quantity': Decimal('1'),
                'unit_measure': 'DOC',
                'unit_price': Decimal('98000'),
                'subtotal': Decimal('98000')
            },
            {
                'product_code': '8 MINIMACK',
                'description': 'SANDALIA NIÑA 18-23 (X6)(WAY INT.)',
                'quantity': Decimal('2'),
                'unit_measure': 'PAR',
                'unit_price': Decimal('84000'),
                'subtotal': Decimal('168000')
            }
        ],
        'totals': {
            'total': Decimal('2765500')
        }
    }
    
    print("📝 Original Invoice Data:")
    print(f"  Invoice: {mock_invoice_data['invoice_number']}")
    print(f"  Supplier: {mock_invoice_data['supplier']['company_name']}")
    print(f"  Items: {len(mock_invoice_data['line_items'])}")
    
    for i, item in enumerate(mock_invoice_data['line_items'], 1):
        print(f"    {i}. {item['product_code']} - {item['quantity']} {item['unit_measure']}")
    
    print("\n🚀 Applying full enhancement...")
    enhanced_data = enhancer.enhance_extracted_data(mock_invoice_data)
    
    print("\n✨ Enhanced Invoice Data:")
    print(f"  Invoice: {enhanced_data['invoice_number']}")
    print(f"  Items: {len(enhanced_data['line_items'])}")
    
    for i, item in enumerate(enhanced_data['line_items'], 1):
        print(f"    {i}. {item['product_code']} (item #{item.get('item_number', 'N/A')})")
        print(f"       Quantity: {item.get('original_quantity')} {item.get('original_unit')} → {item['quantity']} {item['unit_measure']}")
        print(f"       Price: ${item['unit_price']} per {item['unit_measure']}")
        print(f"       Enhancement: {item.get('_enhancement_applied', 'none')}")
        print()
    
    # Show warnings
    warnings = enhanced_data.get('enhancement_warnings', [])
    if warnings:
        print("⚠️  Enhancement Warnings:")
        for warning in warnings:
            print(f"    - {warning}")
    else:
        print("✅ No warnings found")
    
    return enhanced_data

def run_all_tests():
    """Run all tests"""
    print("🧪 TEXTRACT ENHANCEMENT TESTING")
    print("=" * 70)
    print()
    
    try:
        # Test 1: Unit conversions
        enhanced_items = test_unit_conversions()
        print()
        
        # Test 2: Item/Reference separation
        separation_results = test_item_ref_separation()
        print()
        
        # Test 3: Full invoice enhancement
        enhanced_invoice = test_full_invoice_enhancement()
        print()
        
        # Summary
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        # Unit conversion summary
        conversions = sum(1 for item in enhanced_items if item.get('unit_multiplier', 1) > 1)
        print(f"✅ Unit conversions applied: {conversions}/{len(enhanced_items)}")
        
        # Separation summary
        successful_separations = sum(1 for result in separation_results if result['success'])
        print(f"✅ Item/ref separations: {successful_separations}/{len(separation_results)}")
        
        # Overall status
        warnings = enhanced_invoice.get('enhancement_warnings', [])
        print(f"⚠️  Total warnings: {len(warnings)}")
        
        print("\n🎉 All tests completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    if len(sys.argv) > 1 and sys.argv[1] == "units":
        test_unit_conversions()
    elif len(sys.argv) > 1 and sys.argv[1] == "separation":
        test_item_ref_separation()
    elif len(sys.argv) > 1 and sys.argv[1] == "full":
        test_full_invoice_enhancement()
    else:
        run_all_tests()

if __name__ == "__main__":
    main()