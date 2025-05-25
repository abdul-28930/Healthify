# PDF Text Extraction Guide

## Overview

This document explains the enhanced PDF text extraction functionality in the Healthify AI Nutritionist application and provides troubleshooting steps for common issues.

## Features

### Multi-Method Text Extraction

The application now uses multiple PDF text extraction methods in order of preference:

1. **pdfplumber** - Best for structured documents, tables, and modern PDFs
2. **PyMuPDF (fitz)** - Good for various PDF types, including complex layouts
3. **PyPDF2** - Fallback method for simple PDFs
4. **OCR (pytesseract)** - For image-based PDFs (when available)

### Enhanced Blood Test Value Detection

The system can now detect blood test values in various formats:

- Standard format: `Vitamin D: 30 ng/mL`
- Space-separated: `Vitamin D 30 ng/mL`
- Table format: `Vitamin D | 30 | ng/mL`
- Reverse format: `30 ng/mL Vitamin D`
- With aliases: `25(OH)D: 30 ng/mL`, `B12: 400 pg/mL`

### Supported Blood Test Parameters

- Vitamin D (25(OH)D, 25-hydroxyvitamin D)
- Vitamin B12 (B12, Cobalamin)
- Folate (Folic Acid, Vitamin B9)
- Iron (Fe, Serum Iron)
- And many more standard blood chemistry panels

## Installation Requirements

### Basic Requirements (requirements.txt)
```
PyPDF2
pdfplumber
pymupdf
pdf2image
pytesseract
```

### System Dependencies (apt-packages for Streamlit Cloud)
```
tesseract-ocr
libtesseract-dev
poppler-utils
```

## Using the PDF Extraction

### 1. Upload a PDF
- Click "Upload PDF document" in the Document Upload section
- Select your blood test report or health document

### 2. Text Extraction Process
- The system automatically attempts text extraction using multiple methods
- You'll see real-time feedback on the extraction progress
- Statistics show words, characters, and pages detected

### 3. Document Analysis
- Click "Analyze Document" to extract blood test values
- The AI will attempt to identify specific blood test parameters
- Results show values with normal ranges and deficiency indicators

### 4. Results Interpretation
- 🟢 Green: Values within normal range
- 🔴 Red: Values below normal range (potential deficiency)
- 🟠 Orange: Values above normal range

## Troubleshooting

### Common Issues and Solutions

#### 1. "No text could be extracted from this PDF"

**Possible Causes:**
- PDF is image-based (scanned document)
- PDF has complex formatting or is password-protected
- PDF is corrupted

**Solutions:**
- Ensure the PDF contains selectable text (try selecting text manually)
- For scanned documents, OCR will attempt extraction automatically
- Try a different PDF or request a text-based version from your healthcare provider

#### 2. "Text extracted, but no blood values found"

**Possible Causes:**
- Blood test values are not in a recognized format
- The document doesn't contain standard blood chemistry panels
- Values use non-standard units or naming conventions

**Solutions:**
- Manually enter values (e.g., "My Vitamin D is 25 ng/mL")
- Check if your document uses alternative names for tests
- Upload a clearer document with standard lab formatting

#### 3. OCR Not Working on Streamlit Cloud

**Possible Causes:**
- Tesseract OCR not properly installed
- Missing system dependencies

**Solutions:**
- Ensure `apt-packages` file contains required dependencies
- Check Streamlit Cloud logs for OCR-related errors
- For local testing, install Tesseract OCR manually

#### 4. Partial Text Extraction

**Possible Causes:**
- Complex PDF layout
- Mixed text and image content
- Non-standard fonts

**Solutions:**
- The system tries multiple extraction methods automatically
- Check the document preview to see what text was extracted
- Consider providing values manually for missing data

## Testing PDF Extraction

Use the included test script to verify functionality:

```bash
python test_pdf_extraction.py
```

This script will:
- Test all required library imports
- Attempt extraction on any PDF files in the directory
- Show which methods work for your specific PDF

## API Usage Example

```python
# Extract text from uploaded PDF
text = extract_text_from_pdf(pdf_file)

# Analyze with OCR fallback
analysis = analyze_pdf_with_ocr(pdf_path, text)

# Extract blood test values
blood_values = extract_blood_test_values(text)
```

## Best Practices

### For Users
1. **Use text-based PDFs**: Ensure your blood test reports are text-based, not scanned images
2. **Standard formats**: Lab reports from major labs work better than handwritten notes
3. **Clear documents**: Ensure PDFs are not blurry or low resolution
4. **Complete reports**: Upload complete lab reports rather than partial screenshots

### For Developers
1. **Error handling**: Always handle extraction failures gracefully
2. **User feedback**: Provide clear feedback on extraction status
3. **Fallback methods**: Use multiple extraction approaches
4. **Validation**: Validate extracted values for reasonableness

## Supported Formats

### Document Types
- ✅ Standard lab reports (Quest, LabCorp, etc.)
- ✅ Hospital blood test results
- ✅ Doctor's office printouts
- ✅ Digital health app exports
- ⚠️ Scanned/image PDFs (via OCR)
- ❌ Handwritten notes
- ❌ Complex multi-column layouts

### Blood Test Formats
- Standard clinical chemistry panels
- Vitamin and mineral tests
- Complete blood count (CBC)
- Metabolic panels
- Thyroid function tests
- Lipid panels

## Performance Considerations

- Text extraction is fast (< 1 second for most documents)
- OCR processing takes longer (5-10 seconds per page)
- Large PDFs are limited to first 3 pages for OCR
- Memory usage scales with document size

## Privacy and Security

- PDFs are processed locally on the server
- Temporary files are automatically cleaned up
- No document content is stored permanently
- Text extraction happens in memory when possible

---

*For additional support or to report issues with PDF extraction, please check the application logs or contact the development team.* 