#!/usr/bin/env python3
"""
Test script for PDF text extraction functionality
Use this to debug PDF extraction issues
"""

import sys
import os
import io
from pathlib import Path

# Add the current directory to Python path to import modules
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_imports():
    """Test if all required libraries can be imported"""
    print("Testing imports...")
    
    try:
        import PyPDF2
        print("✅ PyPDF2 imported successfully")
    except ImportError as e:
        print(f"❌ PyPDF2 import failed: {e}")
    
    try:
        import pdfplumber
        print("✅ pdfplumber imported successfully")
    except ImportError as e:
        print(f"❌ pdfplumber import failed: {e}")
    
    try:
        import fitz  # PyMuPDF
        print("✅ PyMuPDF (fitz) imported successfully")
    except ImportError as e:
        print(f"❌ PyMuPDF (fitz) import failed: {e}")
    
    try:
        import pytesseract
        print("✅ pytesseract imported successfully")
        try:
            version = pytesseract.get_tesseract_version()
            print(f"  Tesseract version: {version}")
        except Exception as e:
            print(f"  ⚠️ Tesseract not properly configured: {e}")
    except ImportError as e:
        print(f"❌ pytesseract import failed: {e}")
    
    try:
        from pdf2image import convert_from_path
        print("✅ pdf2image imported successfully")
    except ImportError as e:
        print(f"❌ pdf2image import failed: {e}")

def test_pdf_extraction(pdf_path):
    """Test PDF text extraction with different methods"""
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    print(f"\nTesting PDF extraction on: {pdf_path}")
    
    # Test Method 1: pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            if text.strip():
                print(f"✅ pdfplumber extracted {len(text)} characters")
                print(f"   Preview: {text[:100]}...")
            else:
                print("❌ pdfplumber extracted no text")
    except Exception as e:
        print(f"❌ pdfplumber failed: {e}")
    
    # Test Method 2: PyMuPDF
    try:
        import fitz
        pdf_document = fitz.open(pdf_path)
        text = ""
        
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            page_text = page.get_text()
            if page_text:
                text += f"\n--- Page {page_num + 1} ---\n{page_text}"
        
        pdf_document.close()
        
        if text.strip():
            print(f"✅ PyMuPDF extracted {len(text)} characters")
            print(f"   Preview: {text[:100]}...")
        else:
            print("❌ PyMuPDF extracted no text")
    except Exception as e:
        print(f"❌ PyMuPDF failed: {e}")
    
    # Test Method 3: PyPDF2
    try:
        import PyPDF2
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page_text = pdf_reader.pages[page_num].extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            if text.strip():
                print(f"✅ PyPDF2 extracted {len(text)} characters")
                print(f"   Preview: {text[:100]}...")
            else:
                print("❌ PyPDF2 extracted no text")
    except Exception as e:
        print(f"❌ PyPDF2 failed: {e}")

def main():
    """Main test function"""
    print("=== PDF Text Extraction Test ===")
    
    # Test imports first
    test_imports()
    
    # Look for PDF files in current directory
    current_dir = Path(__file__).parent
    pdf_files = list(current_dir.glob("*.pdf"))
    
    if pdf_files:
        print(f"\nFound {len(pdf_files)} PDF file(s) in current directory:")
        for pdf_file in pdf_files:
            print(f"  - {pdf_file.name}")
            test_pdf_extraction(str(pdf_file))
    else:
        print("\nNo PDF files found in current directory.")
        print("Place a PDF file in the same directory as this script to test extraction.")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main() 