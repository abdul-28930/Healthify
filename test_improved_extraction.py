#!/usr/bin/env python3
"""
Test script for improved PDF blood test extraction
Tests various text formats and edge cases
"""

import sys
import os
import re
from chat_nutritionist import (
    extract_blood_test_values, 
    diagnose_extraction_failure,
    provide_extraction_feedback,
    _get_nutrient_aliases
)

def test_extraction_scenarios():
    """Test various blood test text formats"""
    
    test_cases = [
        # Standard format
        {
            "name": "Standard Lab Format",
            "text": """
Lab Results - Quest Diagnostics
Patient: John Smith
Date: 2024-01-15

Vitamin D, 25-Hydroxy: 25 ng/mL (Normal: 30-100)
Vitamin B12: 350 pg/mL (Normal: 200-900)
Iron, Serum: 45 mcg/dL (Normal: 60-170)
Ferritin: 25 ng/mL (Normal: 15-150)
""",
            "expected": ["vitamin_d", "vitamin_b12", "iron", "ferritin"]
        },
        
        # Table format
        {
            "name": "Table Format",
            "text": """
Test Name           | Result | Unit   | Reference Range
Vitamin D (25-OH)   | 32     | ng/mL  | 30-100
B12                 | 450    | pg/mL  | 200-900
Hemoglobin          | 13.5   | g/dL   | 12.0-16.0
Total Cholesterol   | 180    | mg/dL  | 100-200
""",
            "expected": ["vitamin_d", "vitamin_b12", "hemoglobin", "total_cholesterol"]
        },
        
        # Complex multi-column format
        {
            "name": "Multi-column Layout",
            "text": """
COMPREHENSIVE METABOLIC PANEL
Glucose                    95 mg/dL        [70-100]
Sodium                     140 mEq/L       [136-145]
Potassium                  4.2 mEq/L       [3.5-5.0]

LIPID PANEL
Total Cholesterol          195 mg/dL       [<200]
LDL Cholesterol           120 mg/dL       [<100]
HDL Cholesterol            55 mg/dL       [>40]
Triglycerides             135 mg/dL       [<150]
""",
            "expected": ["glucose", "sodium", "potassium", "total_cholesterol", "ldl_cholesterol", "hdl_cholesterol", "triglycerides"]
        },
        
        # Natural language format
        {
            "name": "Natural Language",
            "text": """
Your recent blood test results show:
- Your vitamin D level is 28 ng/mL, which is slightly below the optimal range
- Vitamin B12 result was 275 pg/mL (normal range)
- Iron level measures 55 mcg/dL (low)
- Calcium value is 9.2 mg/dL
- The TSH result is 2.5 mIU/L
""",
            "expected": ["vitamin_d", "vitamin_b12", "iron", "calcium", "tsh"]
        },
        
        # OCR-corrupted text (common OCR issues)
        {
            "name": "OCR Issues",
            "text": """
Vitamin D 25{OH)D        25.8    ng/mL
B-12 Cobalarnin          425     pg/mL  
lron, Serum              75      mcg/dL
Magnesium                1.9     mg/dL
""",
            "expected": ["vitamin_d", "vitamin_b12", "iron", "magnesium"]
        },
        
        # Lab with footnotes and special characters
        {
            "name": "Complex Lab Format",
            "text": """
══════════════════════════════════════════
LABORATORY REPORT - LabCorp
══════════════════════════════════════════

25(OH) Vitamin D          22.5* ng/mL    (30.0-100.0)
Vitamin B-12              350   pg/mL    (200-900)
Folate (Folic Acid)       8.5   ng/mL    (2.7-17.0)
Ferritin                  45†   ng/mL    (15-150)
HbA1c                     5.8%           (4.0-5.6)

* Below normal range
† Within normal limits
""",
            "expected": ["vitamin_d", "vitamin_b12", "folate", "ferritin", "hba1c"]
        }
    ]
    
    print("🧪 Testing Improved Blood Test Extraction")
    print("=" * 50)
    
    total_tests = len(test_cases)
    passed_tests = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}/{total_tests}: {test_case['name']}")
        print("-" * 30)
        
        # Extract values
        extracted = extract_blood_test_values(test_case['text'])
        
        # Check results
        found_nutrients = list(extracted.keys())
        expected_nutrients = test_case['expected']
        
        print(f"Expected: {expected_nutrients}")
        print(f"Found:    {found_nutrients}")
        
        # Calculate success metrics
        found_expected = sum(1 for nutrient in expected_nutrients if nutrient in found_nutrients)
        false_positives = sum(1 for nutrient in found_nutrients if nutrient not in expected_nutrients)
        
        success_rate = (found_expected / len(expected_nutrients)) * 100 if expected_nutrients else 0
        
        if success_rate >= 80:  # 80% success rate threshold
            print(f"✅ PASS ({success_rate:.1f}% success rate)")
            passed_tests += 1
        else:
            print(f"❌ FAIL ({success_rate:.1f}% success rate)")
            
        if extracted:
            print("Extracted values:")
            for nutrient, value in extracted.items():
                print(f"  • {nutrient}: {value}")
        else:
            print("❌ No values extracted")
            
        # Show diagnostic info for failed cases
        if success_rate < 80:
            diagnosis = diagnose_extraction_failure(test_case['text'], extracted)
            if diagnosis['potential_issues']:
                print("Issues:", ', '.join(diagnosis['potential_issues']))
    
    print(f"\n🎯 Overall Results: {passed_tests}/{total_tests} tests passed ({(passed_tests/total_tests)*100:.1f}%)")
    return passed_tests == total_tests

def test_alias_coverage():
    """Test alias coverage for common blood test names"""
    print("\n🏷️  Testing Alias Coverage")
    print("=" * 30)
    
    aliases = _get_nutrient_aliases()
    
    common_test_names = [
        "25(OH)D", "B12", "Ferritin", "Hgb", "TSH", "A1c", 
        "LDL", "HDL", "ALT", "AST", "CRP", "Glucose"
    ]
    
    coverage_count = 0
    for test_name in common_test_names:
        found = False
        for nutrient, nutrient_aliases in aliases.items():
            if test_name in nutrient_aliases or test_name.lower() in nutrient_aliases:
                found = True
                print(f"✅ {test_name} → {nutrient}")
                break
        
        if found:
            coverage_count += 1
        else:
            print(f"❌ {test_name} → No mapping found")
    
    coverage_rate = (coverage_count / len(common_test_names)) * 100
    print(f"\n📊 Alias Coverage: {coverage_count}/{len(common_test_names)} ({coverage_rate:.1f}%)")
    return coverage_rate >= 90

def test_feedback_system():
    """Test the diagnostic feedback system"""
    print("\n🔧 Testing Feedback System")
    print("=" * 30)
    
    # Test case with no blood values
    empty_text = "This is a general health document with no blood test values."
    diagnosis = diagnose_extraction_failure(empty_text, {})
    
    print("Empty document diagnosis:")
    print(f"  Quality: {diagnosis['text_quality']}")
    print(f"  Issues: {len(diagnosis['potential_issues'])}")
    print(f"  Suggestions: {len(diagnosis['suggestions'])}")
    
    # Test case with blood indicators but no extracted values
    partial_text = """
Lab Report - Patient Blood Tests
Vitamin D level was checked
Iron studies were performed
Results are pending review
    """
    
    diagnosis2 = diagnose_extraction_failure(partial_text, {})
    
    print("\nPartial document diagnosis:")
    print(f"  Quality: {diagnosis2['text_quality']}")
    print(f"  Patterns found: {len(diagnosis2['detected_patterns'])}")
    print(f"  Issues: {len(diagnosis2['potential_issues'])}")
    
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Enhanced PDF Extraction Tests")
    print("=" * 50)
    
    all_passed = True
    
    # Test extraction scenarios
    if not test_extraction_scenarios():
        all_passed = False
    
    # Test alias coverage
    if not test_alias_coverage():
        all_passed = False
    
    # Test feedback system
    if not test_feedback_system():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED! The improved extraction system is working well.")
    else:
        print("⚠️  Some tests failed. Review the output above for details.")
    
    print("\n💡 Key Improvements Implemented:")
    print("   • Multi-strategy extraction (patterns, tables, positional, NLP)")
    print("   • Comprehensive alias support (60+ blood test parameters)")
    print("   • Confidence scoring and validation")
    print("   • Enhanced diagnostic feedback")
    print("   • Better OCR error handling")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 