import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import tempfile
import base64
from datetime import datetime
import json
import re
import openai
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from typing import Dict, List, Any, Optional, Tuple
import plotly.express as px
import plotly.graph_objects as go
from config import OPENAI_API_KEY, OPENAI_MODEL, BLOOD_TEST_RANGES, DAILY_NUTRITION_REQUIREMENTS

# Initialize OpenAI
if OPENAI_API_KEY:
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        use_legacy = False
    except Exception:
        # Fallback to legacy OpenAI
        openai.api_key = OPENAI_API_KEY
        client = openai
        use_legacy = True
else:
    st.error("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
    st.stop()

# Cache OCR setup for document analysis
@st.cache_resource
def setup_ocr():
    """Initialize OCR-related resources optimized for Streamlit Cloud"""
    try:
        # Detect if running on Streamlit Cloud
        is_streamlit_cloud = os.getenv('STREAMLIT_SHARING_MODE') is not None or os.path.exists('/mount/src')
        
        if is_streamlit_cloud:
            # Streamlit Cloud specific setup
            st.info("🔧 Setting up OCR for Streamlit Cloud...")
            
            # Streamlit Cloud typically has tesseract at /usr/bin/tesseract
            tesseract_paths = [
                '/usr/bin/tesseract',
                '/usr/local/bin/tesseract'
            ]
            
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
            else:
                st.warning("⚠️ Tesseract not found in expected Streamlit Cloud locations")
                return False
        else:
            # Local development setup
            possible_paths = [
                '/usr/bin/tesseract',  # Linux
                '/usr/local/bin/tesseract',  # Some Linux/Mac
                'C:/Program Files/Tesseract-OCR/tesseract.exe',  # Windows
                'C:/Program Files (x86)/Tesseract-OCR/tesseract.exe',  # Windows (32-bit)
                '/opt/homebrew/bin/tesseract',  # Mac with Homebrew (M1)
                '/usr/local/Cellar/tesseract/*/bin/tesseract'  # Mac with Homebrew (Intel)
            ]
            
            tesseract_cmd = None
            for path in possible_paths:
                if os.path.exists(path):
                    tesseract_cmd = path
                    break
            
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Test Tesseract installation
        try:
            version = pytesseract.get_tesseract_version()
            st.success(f"✅ OCR ready (Tesseract {version})")
            return True
        except Exception as e:
            st.warning(f"⚠️ OCR test failed: {str(e)}")
            return False
        
    except pytesseract.TesseractNotFoundError:
        if is_streamlit_cloud:
            st.error("❌ Tesseract not available on Streamlit Cloud. Please check packages.txt configuration.")
        else:
            st.warning("⚠️ Tesseract OCR not found. Image-based PDF analysis will be limited.")
        return False
    except Exception as e:
        st.warning(f"⚠️ OCR setup issue: {str(e)}. Some features may be limited.")
        return False

# Page configuration
st.set_page_config(
    page_title="AI Nutritionist Chat - Healthify",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        display: flex;
        align-items: flex-start;
    }
    .user-message {
        background-color: #e9f7ef;
        border-left: 4px solid #4CAF50;
    }
    .bot-message {
        background-color: #f9f9f9;
        border-left: 4px solid #2196F3;
    }
    .message-content {
        margin-left: 1rem;
    }
    .document-preview {
        border: 1px solid #ddd;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .warning-box {
        background: #fff3cd;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    .success-box {
        background: #d4edda;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .info-box {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    """Initialize session state variables for chat and user profile"""
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "👋 Hello! I'm Dr. NutriBot, your AI nutritionist specializing in nutritional deficiency detection. I can:\n\n1️⃣ **Analyze your blood test reports** to identify deficiencies and abnormalities\n2️⃣ **Examine your current diet** to flag missing essential nutrients\n3️⃣ **Connect the dots** between your blood tests and dietary habits\n4️⃣ **Recommend specific foods** to address your nutritional gaps\n\nYou can upload a blood test PDF, describe your typical daily meals, or ask me to analyze specific foods to identify missing nutrients. How would you like to start?"}
        ]
    
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = {
            "age": None,
            "gender": None,
            "weight": None,
            "height": None,
            "activity_level": None,
            "health_conditions": None,
            "medications": None,
            "dietary_restrictions": None,
            "health_goals": None
        }
    
    if 'blood_test_results' not in st.session_state:
        st.session_state.blood_test_results = {}
    
    if 'document_analysis' not in st.session_state:
        st.session_state.document_analysis = None
    
    if 'onboarding_complete' not in st.session_state:
        st.session_state.onboarding_complete = False
    
    if 'current_step' not in st.session_state:
        st.session_state.current_step = "welcome"

def extract_text_from_pdf(pdf_file):
    """Enhanced text extraction from uploaded PDF file using multiple methods"""
    text = ""
    extraction_method = "None"
    
    try:
        # Method 1: Try pdfplumber first (best for structured documents)
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                        extraction_method = "pdfplumber"
                if text.strip():
                    st.success(f"✅ Text extracted successfully using {extraction_method}")
                    return text
        except Exception as e:
            st.warning(f"pdfplumber extraction failed: {str(e)}")
        
        # Method 2: Try PyMuPDF (good for various PDF types)
        try:
            # Reset file pointer
            pdf_file.seek(0)
            pdf_bytes = pdf_file.read()
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                page_text = page.get_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                    extraction_method = "PyMuPDF"
            
            pdf_document.close()
            if text.strip():
                st.success(f"✅ Text extracted successfully using {extraction_method}")
                return text
        except Exception as e:
            st.warning(f"PyMuPDF extraction failed: {str(e)}")
        
        # Method 3: Fallback to PyPDF2
        try:
            pdf_file.seek(0)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                page_text = pdf_reader.pages[page_num].extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                    extraction_method = "PyPDF2"
            if text.strip():
                st.info(f"ℹ️ Text extracted using {extraction_method} (fallback method)")
                return text
        except Exception as e:
            st.warning(f"PyPDF2 extraction failed: {str(e)}")
        
        # If we get here, direct text extraction failed
        if not text.strip():
            st.warning("⚠️ Direct text extraction failed. The PDF might be image-based or poorly formatted.")
            return ""
            
    except Exception as e:
        st.error(f"❌ Unexpected error during text extraction: {str(e)}")
        return ""
    
    return text

def analyze_pdf_with_ocr(pdf_path, extracted_text=""):
    """Enhanced PDF document analysis optimized for Streamlit Cloud"""
    try:
        # If we already have extracted text, use it
        if extracted_text.strip():
            st.info("📄 Using previously extracted text for analysis")
            test_results = extract_blood_test_values(extracted_text)
            return {
                "full_text": extracted_text,
                "structured_data": test_results,
                "method": "direct_extraction"
            }
        
        # Detect environment
        is_streamlit_cloud = os.getenv('STREAMLIT_SHARING_MODE') is not None or os.path.exists('/mount/src')
        
        # Try direct extraction methods first (these are faster and more reliable)
        try:
            with open(pdf_path, 'rb') as file:
                # Method 1: Try pdfplumber (most reliable for structured documents)
                try:
                    with pdfplumber.open(file) as pdf:
                        # Limit pages for cloud deployment to manage memory
                        max_pages = 5 if is_streamlit_cloud else 10
                        direct_text = ""
                        
                        for page_num, page in enumerate(pdf.pages[:max_pages]):
                            page_text = page.extract_text()
                            if page_text:
                                direct_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                        
                        if direct_text.strip():
                            test_results = extract_blood_test_values(direct_text)
                            return {
                                "full_text": direct_text,
                                "structured_data": test_results,
                                "method": "pdfplumber"
                            }
                except Exception as e:
                    st.info(f"pdfplumber analysis failed: {str(e)}")
                
                # Method 2: Try PyMuPDF (fallback)
                try:
                    file.seek(0)
                    pdf_bytes = file.read()
                    
                    # Memory optimization for cloud
                    if len(pdf_bytes) > 10 * 1024 * 1024:  # 10MB limit for cloud
                        st.warning("⚠️ Large PDF detected. Processing may be limited on Streamlit Cloud.")
                    
                    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                    
                    direct_text = ""
                    max_pages = 5 if is_streamlit_cloud else pdf_document.page_count
                    
                    for page_num in range(min(max_pages, pdf_document.page_count)):
                        page = pdf_document[page_num]
                        page_text = page.get_text()
                        if page_text:
                            direct_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                    
                    pdf_document.close()
                    
                    if direct_text.strip():
                        test_results = extract_blood_test_values(direct_text)
                        return {
                            "full_text": direct_text,
                            "structured_data": test_results,
                            "method": "PyMuPDF"
                        }
                except Exception as e:
                    st.info(f"PyMuPDF analysis failed: {str(e)}")
                
        except Exception as e:
            st.warning(f"Direct extraction methods failed: {str(e)}")
        
        # OCR as last resort (most resource intensive)
        ocr_available = setup_ocr()
        
        if ocr_available:
            try:
                st.info("🔍 Attempting OCR analysis (this may take longer on Streamlit Cloud)...")
                
                # Cloud-optimized OCR settings
                if is_streamlit_cloud:
                    # Use system poppler path for Streamlit Cloud
                    poppler_path = '/usr/bin'
                    max_pages_ocr = 2  # Limit to 2 pages for cloud
                else:
                    poppler_path = '/usr/bin' if os.path.exists('/usr/bin/pdftoppm') else None
                    max_pages_ocr = 3
                
                # Convert PDF to images with memory optimization
                try:
                    images = convert_from_path(
                        pdf_path, 
                        poppler_path=poppler_path, 
                        first_page=1, 
                        last_page=max_pages_ocr,
                        dpi=150 if is_streamlit_cloud else 300,  # Lower DPI for cloud
                        fmt='jpeg'  # More memory efficient
                    )
                except Exception as e:
                    st.error(f"PDF to image conversion failed: {str(e)}")
                    if is_streamlit_cloud:
                        st.error("This might be due to Streamlit Cloud resource limitations. Try a smaller PDF or better quality text-based PDF.")
                    return {
                        "full_text": "",
                        "structured_data": {},
                        "error": f"PDF conversion failed: {str(e)}",
                        "method": "failed"
                    }
                
                ocr_text = ""
                
                for i, image in enumerate(images):
                    try:
                        # Memory optimization: process smaller images on cloud
                        if is_streamlit_cloud:
                            # Resize image to reduce memory usage
                            max_size = (1200, 1600)
                            image.thumbnail(max_size, Image.Resampling.LANCZOS)
                        
                        # Convert to grayscale for better OCR and less memory
                        gray_image = image.convert('L')
                        
                        # Cloud-optimized OCR config
                        if is_streamlit_cloud:
                            custom_config = r'--oem 3 --psm 6 -c tessedit_do_invert=0'
                        else:
                            custom_config = r'--oem 3 --psm 6'
                        
                        page_text = pytesseract.image_to_string(gray_image, config=custom_config)
                        ocr_text += f"\n--- Page {i+1} (OCR) ---\n{page_text}"
                        
                        # Clear image from memory
                        del gray_image, image
                        
                    except Exception as e:
                        st.warning(f"Error processing page {i+1} with OCR: {str(e)}")
                        continue
                
                if ocr_text.strip():
                    test_results = extract_blood_test_values(ocr_text)
                    
                    return {
                        "full_text": ocr_text,
                        "structured_data": test_results,
                        "method": "OCR"
                    }
                
            except Exception as e:
                error_msg = f"OCR processing failed: {str(e)}"
                if is_streamlit_cloud:
                    error_msg += " (Streamlit Cloud has limited OCR resources)"
                st.warning(error_msg)
        else:
            if is_streamlit_cloud:
                st.info("🔍 OCR not available. This is normal on Streamlit Cloud if packages.txt is not properly configured.")
            else:
                st.warning("🔍 OCR is not available. Install tesseract-ocr for image-based PDF analysis.")
        
        # If all methods failed
        return {
            "full_text": "",
            "structured_data": {},
            "error": "Could not extract text from the document using any available method",
            "method": "failed"
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in document analysis: {str(e)}"
        st.error(error_msg)
        return {
            "full_text": "",
            "structured_data": {},
            "error": error_msg,
            "method": "error"
        }

def extract_blood_test_values(text):
    """Enhanced extraction of blood test values from document text with multiple parsing strategies"""
    blood_values = {}
    confidence_scores = {}
    
    # Clean up the text for better matching
    cleaned_text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    
    # Strategy 1: Direct pattern matching with enhanced aliases
    blood_values_1, scores_1 = _extract_with_patterns(cleaned_text)
    blood_values.update(blood_values_1)
    confidence_scores.update(scores_1)
    
    # Strategy 2: Table structure detection
    blood_values_2, scores_2 = _extract_from_tables(text)
    for k, v in blood_values_2.items():
        if k not in blood_values or scores_2[k] > confidence_scores.get(k, 0):
            blood_values[k] = v
            confidence_scores[k] = scores_2[k]
    
    # Strategy 3: Positional parsing (line-by-line)
    blood_values_3, scores_3 = _extract_positional(text)
    for k, v in blood_values_3.items():
        if k not in blood_values or scores_3[k] > confidence_scores.get(k, 0):
            blood_values[k] = v
            confidence_scores[k] = scores_3[k]
    
    # Strategy 4: NLP-style extraction (more flexible patterns)
    blood_values_4, scores_4 = _extract_with_nlp_patterns(text)
    for k, v in blood_values_4.items():
        if k not in blood_values or scores_4[k] > confidence_scores.get(k, 0):
            blood_values[k] = v
            confidence_scores[k] = scores_4[k]
    
    # Strategy 5: Fallback extraction for common edge cases
    blood_values_5, scores_5 = _extract_fallback_patterns(text)
    for k, v in blood_values_5.items():
        if k not in blood_values or scores_5[k] > confidence_scores.get(k, 0):
            blood_values[k] = v
            confidence_scores[k] = scores_5[k]
    
    # Filter out values that are clearly wrong (too high/low)
    filtered_values = {}
    for nutrient, value in blood_values.items():
        if _is_reasonable_value(nutrient, value):
            filtered_values[nutrient] = value
    
    return filtered_values

def _get_nutrient_aliases():
    """Get comprehensive aliases for blood test parameters"""
    aliases = {
        # Vitamins
        'vitamin_d': [
            '25(OH)D', '25-hydroxyvitamin D', '25-OH-D', 'Vit D', 'VitD', 'Vitamin D3',
            'Vitamin D2', 'Calcidiol', '25-Hydroxy Vitamin D', 'Cholecalciferol',
            'D2', 'D3', '25OHD', 'Vit-D', 'VIT D TOTAL', 'Vitamin D 25-OH'
        ],
        'vitamin_b12': [
            'B12', 'B-12', 'Cobalamin', 'Vit B12', 'VitB12', 'Cyanocobalamin',
            'Methylcobalamin', 'B 12', 'VIT B12', 'VITAMIN B-12', 'Cbl'
        ],
        'folate': [
            'Folic Acid', 'Vitamin B9', 'B9', 'B-9', 'Folacin', 'Pteroylglutamic Acid',
            'FOLIC ACID', 'FOL', 'B 9', 'Serum Folate', 'RBC Folate'
        ],
        'vitamin_c': [
            'Ascorbic Acid', 'Vit C', 'VitC', 'Ascorbate', 'L-Ascorbic Acid'
        ],
        'vitamin_a': [
            'Retinol', 'Vit A', 'VitA', 'Beta Carotene', 'Retinyl Palmitate'
        ],
        'vitamin_e': [
            'Tocopherol', 'Alpha-Tocopherol', 'Vit E', 'VitE'
        ],
        
        # Minerals and Trace Elements
        'iron': [
            'Fe', 'Serum Iron', 'Iron Serum', 'SI', 'TIBC', 'Iron (Fe)', 'FE SERUM'
        ],
        'ferritin': [
            'Ferritin Serum', 'Serum Ferritin', 'FERR', 'FER', 'Storage Iron', 'Ferritin'
        ],
        'transferrin_saturation': [
            'TSAT', 'Transferrin Sat', 'Iron Saturation', 'Fe Saturation', 'TIBC Saturation'
        ],
        'calcium': [
            'Ca', 'Serum Calcium', 'Calcium Serum', 'CA', 'Total Calcium', 'Ionized Calcium',
            'Ca++', 'Calcium Total'
        ],
        'magnesium': [
            'Mg', 'Serum Magnesium', 'Magnesium Serum', 'MG', 'Mag'
        ],
        'zinc': [
            'Zn', 'Serum Zinc', 'Zinc Serum', 'ZN'
        ],
        'copper': [
            'Cu', 'Serum Copper', 'Copper Serum', 'CU'
        ],
        'selenium': [
            'Se', 'Serum Selenium', 'Selenium Serum', 'SE'
        ],
        
        # Blood Chemistry
        'hemoglobin': [
            'Hgb', 'Hb', 'HGB', 'Hemoglobin', 'Haemoglobin'
        ],
        'hematocrit': [
            'Hct', 'HCT', 'Hematocrit', 'Haematocrit', 'Packed Cell Volume', 'PCV'
        ],
        'mch': [
            'MCH', 'Mean Corpuscular Hemoglobin'
        ],
        'mcv': [
            'MCV', 'Mean Corpuscular Volume'
        ],
        'mchc': [
            'MCHC', 'Mean Corpuscular Hemoglobin Concentration'
        ],
        'rbc': [
            'RBC', 'Red Blood Cells', 'Red Blood Cell Count', 'Erythrocytes'
        ],
        'wbc': [
            'WBC', 'White Blood Cells', 'White Blood Cell Count', 'Leukocytes'
        ],
        'platelets': [
            'PLT', 'Platelet Count', 'Thrombocytes'
        ],
        
        # Metabolic Panel
        'glucose': [
            'Gluc', 'GLU', 'Blood Sugar', 'Blood Glucose', 'Fasting Glucose', 'FPG', 'Glucose'
        ],
        'hba1c': [
            'HbA1c', 'A1c', 'Hemoglobin A1c', 'Glycated Hemoglobin', 'HgbA1c'
        ],
        'creatinine': [
            'Creat', 'CREAT', 'Serum Creatinine'
        ],
        'bun': [
            'BUN', 'Blood Urea Nitrogen', 'Urea Nitrogen'
        ],
        'sodium': [
            'Na', 'NA', 'Serum Sodium'
        ],
        'potassium': [
            'K', 'K+', 'Serum Potassium'
        ],
        'chloride': [
            'Cl', 'CL', 'Serum Chloride'
        ],
        'co2': [
            'CO2', 'Carbon Dioxide', 'Bicarbonate', 'HCO3'
        ],
        
        # Lipid Panel
        'total_cholesterol': [
            'Total Chol', 'CHOL', 'Cholesterol Total', 'TC'
        ],
        'ldl_cholesterol': [
            'LDL', 'LDL Chol', 'LDL Cholesterol', 'Low Density Lipoprotein'
        ],
        'hdl_cholesterol': [
            'HDL', 'HDL Chol', 'HDL Cholesterol', 'High Density Lipoprotein'
        ],
        'triglycerides': [
            'TRIG', 'TG', 'Triglyceride', 'Triacylglycerol'
        ],
        
        # Liver Function
        'alt': [
            'ALT', 'SGPT', 'Alanine Aminotransferase', 'Alanine Transaminase'
        ],
        'ast': [
            'AST', 'SGOT', 'Aspartate Aminotransferase', 'Aspartate Transaminase'
        ],
        'alkaline_phosphatase': [
            'ALP', 'Alk Phos', 'Alkaline Phos', 'ALKP'
        ],
        'bilirubin_total': [
            'Total Bili', 'TBILI', 'Bilirubin', 'Total Bilirubin'
        ],
        'albumin': [
            'ALB', 'Serum Albumin'
        ],
        'total_protein': [
            'TP', 'Total Prot', 'Serum Protein'
        ],
        
        # Thyroid Function
        'tsh': [
            'TSH', 'Thyroid Stimulating Hormone', 'Thyrotropin'
        ],
        't4_free': [
            'Free T4', 'FT4', 'Free Thyroxine', 'T4 Free'
        ],
        't3_free': [
            'Free T3', 'FT3', 'Free Triiodothyronine', 'T3 Free'
        ],
        
        # Inflammatory Markers
        'crp': [
            'CRP', 'C-Reactive Protein', 'C Reactive Protein', 'hs-CRP', 'hsCRP'
        ],
        'esr': [
            'ESR', 'Sed Rate', 'Sedimentation Rate', 'Erythrocyte Sedimentation Rate'
        ],
        
        # Hormones
        'testosterone': [
            'Test', 'TESTO', 'Total Testosterone', 'Free Testosterone'
        ],
        'estradiol': [
            'E2', 'Estrogen', 'Oestradiol'
        ],
        'cortisol': [
            'CORT', 'Serum Cortisol', 'Morning Cortisol'
        ],
        'insulin': [
            'INS', 'Serum Insulin', 'Fasting Insulin'
        ],
        
        # Other Important Markers
        'homocysteine': [
            'Hcy', 'HCYS', 'Homocys'
        ],
        'uric_acid': [
            'Uric', 'UA', 'Serum Uric Acid'
        ],
        'phosphorus': [
            'Phos', 'P', 'PO4', 'Serum Phosphorus', 'Phosphate'
        ]
    }
    return aliases

def _extract_with_patterns(text):
    """Enhanced pattern-based extraction with comprehensive alias support"""
    blood_values = {}
    confidence_scores = {}
    aliases = _get_nutrient_aliases()
    
    for nutrient, info in BLOOD_TEST_RANGES.items():
        nutrient_name = nutrient.replace('_', ' ')
        all_variations = [
            nutrient_name, nutrient_name.replace(' ', ''), 
            nutrient_name.replace(' ', '_'), nutrient_name.replace(' ', '-')
        ]
        
        # Add aliases if available
        if nutrient in aliases:
            all_variations.extend(aliases[nutrient])
        
        best_match = None
        best_confidence = 0
        
        for variation in all_variations:
            patterns = [
                # Pattern 1: Standard colon format
                (rf"(?i){re.escape(variation)}\s*[:=]\s*(\d+\.?\d*)\s*{re.escape(info['unit'])}", 0.9),
                # Pattern 2: Space-separated
                (rf"(?i){re.escape(variation)}\s+(\d+\.?\d*)\s*{re.escape(info['unit'])}", 0.8),
                # Pattern 3: Reverse order
                (rf"(?i)(\d+\.?\d*)\s*{re.escape(info['unit'])}\s+{re.escape(variation)}", 0.8),
                # Pattern 4: Table with separators
                (rf"(?i){re.escape(variation)}\s*[|,:;]\s*(\d+\.?\d*)\s*[|,:;]?\s*{re.escape(info['unit'])}", 0.7),
                # Pattern 5: Multi-space/tab separation
                (rf"(?i){re.escape(variation)}\s{{2,}}(\d+\.?\d*)\s*{re.escape(info['unit'])}", 0.7),
                # Pattern 6: Without units (lower confidence)
                (rf"(?i){re.escape(variation)}\s*[:=]\s*(\d+\.?\d*)", 0.5),
                # Pattern 7: Parenthetical values
                (rf"(?i){re.escape(variation)}\s*\(\s*(\d+\.?\d*)\s*{re.escape(info['unit'])}\s*\)", 0.6),
                # Pattern 8: Range format (take first value)
                (rf"(?i){re.escape(variation)}\s*[:=]\s*(\d+\.?\d*)\s*-\s*\d+\.?\d*\s*{re.escape(info['unit'])}", 0.6),
                # Pattern 9: With comma separators (looser)
                (rf"(?i){re.escape(variation)}\s*[,]\s*(\d+\.?\d*)\s*{re.escape(info['unit'])}", 0.6),
                # Pattern 10: Flexible spacing around units
                (rf"(?i){re.escape(variation)}\s*[:=]?\s*(\d+\.?\d*)\s+{re.escape(info['unit'])}", 0.7),
                # Pattern 11: Without units but with colon (more flexible)
                (rf"(?i){re.escape(variation)}\s*[:]\s*(\d+\.?\d*)", 0.6),
                # Pattern 12: Numbers with potential special characters
                (rf"(?i){re.escape(variation)}\s*[:=]?\s*(\d+\.?\d*)[*†‡§]?\s*{re.escape(info['unit'])}", 0.8),
                # Pattern 13: Lab format with comma and descriptive text
                (rf"(?i){re.escape(variation)}\s*[,][\w\s-]*[:]\s*(\d+\.?\d*)\s*{re.escape(info['unit'])}", 0.8),
                # Pattern 14: Flexible lab format (allowing text before colon)
                (rf"(?i){re.escape(variation)}[\w\s,.-]*[:]\s*(\d+\.?\d*)\s*{re.escape(info['unit'])}", 0.7),
                # Pattern 15: Very flexible pattern for common lab formats
                (rf"(?i){re.escape(variation)}[^:]*[:]\s*(\d+\.?\d*)\s*{re.escape(info['unit'])}", 0.6)
            ]
            
            for pattern, confidence in patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        value = float(match.group(1))
                        if _is_reasonable_value(nutrient, value) and confidence > best_confidence:
                            best_match = value
                            best_confidence = confidence
                    except (ValueError, IndexError):
                        continue
        
        if best_match is not None:
            blood_values[nutrient] = best_match
            confidence_scores[nutrient] = best_confidence
    
    return blood_values, confidence_scores

def _extract_from_tables(text):
    """Extract values from table-like structures"""
    blood_values = {}
    confidence_scores = {}
    
    # Split text into lines and look for table patterns
    lines = text.split('\n')
    aliases = _get_nutrient_aliases()
    
    for i, line in enumerate(lines):
        # Look for table headers or separators
        if re.search(r'[|]{2,}|[-]{3,}|[=]{3,}', line):
            continue
            
        # Try to parse table-like rows
        # Common patterns: "Test Name | Value | Unit | Range"
        table_patterns = [
            r'([^|]+)\s*\|\s*(\d+\.?\d*)\s*\|\s*([^|]+)\s*\|',  # Pipe-separated
            r'([^\t]+)\t+(\d+\.?\d*)\t+([^\t]+)',  # Tab-separated
            r'(.{20,40})\s{3,}(\d+\.?\d*)\s{2,}([^\s]+)',  # Space-aligned columns
        ]
        
        for pattern in table_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                test_name = match.group(1).strip()
                try:
                    value = float(match.group(2))
                    unit = match.group(3).strip()
                    
                    # Try to match to known nutrients
                    matched_nutrient = _match_test_name_to_nutrient(test_name, unit, aliases)
                    if matched_nutrient and _is_reasonable_value(matched_nutrient, value):
                        blood_values[matched_nutrient] = value
                        confidence_scores[matched_nutrient] = 0.8
                        
                except (ValueError, IndexError):
                    continue
    
    return blood_values, confidence_scores

def _extract_positional(text):
    """Extract values using positional analysis for complex layouts"""
    blood_values = {}
    confidence_scores = {}
    
    # Split into lines and analyze positioning
    lines = text.split('\n')
    aliases = _get_nutrient_aliases()
    
    # Look for patterns where test names and values might be separated by distance
    for line in lines:
        # Remove excessive whitespace but preserve structure
        cleaned_line = re.sub(r'\s{2,}', ' | ', line.strip())
        
        # Split by the pipe separators we created
        parts = [p.strip() for p in cleaned_line.split('|') if p.strip()]
        
        if len(parts) >= 2:
            for i in range(len(parts) - 1):
                test_name = parts[i]
                
                # Check if next part looks like a value
                for j in range(i + 1, len(parts)):
                    potential_value = parts[j]
                    value_match = re.search(r'(\d+\.?\d*)', potential_value)
                    
                    if value_match:
                        try:
                            value = float(value_match.group(1))
                            
                            # Try to extract unit from the same part or nearby parts
                            unit = _extract_unit_from_context(potential_value, parts[j:])
                            
                            matched_nutrient = _match_test_name_to_nutrient(test_name, unit, aliases)
                            if matched_nutrient and _is_reasonable_value(matched_nutrient, value):
                                blood_values[matched_nutrient] = value
                                confidence_scores[matched_nutrient] = 0.6
                                break
                                
                        except ValueError:
                            continue
    
    return blood_values, confidence_scores

def _extract_with_nlp_patterns(text):
    """Use natural language processing patterns for complex extraction"""
    blood_values = {}
    confidence_scores = {}
    aliases = _get_nutrient_aliases()
    
    # Look for natural language patterns
    sentences = re.split(r'[.!?]\s+', text)
    
    for sentence in sentences:
        # Pattern: "Your vitamin D level is 25 ng/mL"
        nlp_patterns = [
            r'(?i)(\w+(?:\s+\w+)*?)\s+(?:level|value|result|is|was|measures?)\s+(\d+\.?\d*)\s*([a-z/μ]+)',
            r'(?i)(\w+(?:\s+\w+)*?)\s*[:\-]\s*(\d+\.?\d*)\s*([a-z/μ]+)',
            r'(?i)(?:level|value|result)\s+of\s+(\w+(?:\s+\w+)*?)\s+(?:is|was)\s+(\d+\.?\d*)\s*([a-z/μ]+)',
        ]
        
        for pattern in nlp_patterns:
            matches = re.finditer(pattern, sentence)
            for match in matches:
                test_name = match.group(1).strip()
                try:
                    value = float(match.group(2))
                    unit = match.group(3).strip()
                    
                    matched_nutrient = _match_test_name_to_nutrient(test_name, unit, aliases)
                    if matched_nutrient and _is_reasonable_value(matched_nutrient, value):
                        if matched_nutrient not in blood_values:  # Don't override higher confidence matches
                            blood_values[matched_nutrient] = value
                            confidence_scores[matched_nutrient] = 0.7
                            
                except (ValueError, IndexError):
                    continue
    
    return blood_values, confidence_scores

def _extract_fallback_patterns(text):
    """Fallback extraction for common edge cases"""
    blood_values = {}
    confidence_scores = {}
    aliases = _get_nutrient_aliases()
    
    # Simple fallback patterns for very common tests
    fallback_patterns = [
        # Vitamin D patterns
        (r'(?i)vitamin\s*d[^:]*:\s*(\d+\.?\d*)', 'vitamin_d', 0.6),
        (r'(?i)25\s*(?:oh|hydroxy)[^:]*:\s*(\d+\.?\d*)', 'vitamin_d', 0.7),
        # B12 patterns
        (r'(?i)b[\s-]?12[^:]*:\s*(\d+\.?\d*)', 'vitamin_b12', 0.7),
        (r'(?i)cobalamin[^:]*:\s*(\d+\.?\d*)', 'vitamin_b12', 0.6),
        # Iron patterns
        (r'(?i)iron[^:]*:\s*(\d+\.?\d*)', 'iron', 0.6),
        (r'(?i)ferritin[^:]*:\s*(\d+\.?\d*)', 'ferritin', 0.7),
        # Hemoglobin patterns
        (r'(?i)h(?:e|a)moglobin[^:]*:\s*(\d+\.?\d*)', 'hemoglobin', 0.6),
        (r'(?i)hgb[^:]*:\s*(\d+\.?\d*)', 'hemoglobin', 0.7),
        # Common metabolic panel
        (r'(?i)glucose[^:]*:\s*(\d+\.?\d*)', 'glucose', 0.6),
        (r'(?i)cholesterol[^:]*:\s*(\d+\.?\d*)', 'total_cholesterol', 0.6),
        # Very simple number extraction after common terms
        (r'(?i)(?:vitamin|vit)\s*d[^\d]*(\d+\.?\d*)', 'vitamin_d', 0.5),
        (r'(?i)b\s*12[^\d]*(\d+\.?\d*)', 'vitamin_b12', 0.5),
    ]
    
    for pattern, nutrient, confidence in fallback_patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                value = float(matches[0])
                if nutrient not in blood_values or confidence > confidence_scores.get(nutrient, 0):
                    blood_values[nutrient] = value
                    confidence_scores[nutrient] = confidence
            except (ValueError, IndexError):
                continue
    
    return blood_values, confidence_scores

def _match_test_name_to_nutrient(test_name, unit, aliases):
    """Match a test name to a known nutrient using aliases and fuzzy matching"""
    test_name_lower = test_name.lower().strip()
    
    # Direct matching with aliases
    for nutrient, nutrient_aliases in aliases.items():
        # Check primary name
        if nutrient.replace('_', ' ').lower() in test_name_lower:
            if _unit_matches(unit, nutrient):
                return nutrient
        
        # Check aliases
        for alias in nutrient_aliases:
            if alias.lower() in test_name_lower:
                if _unit_matches(unit, nutrient):
                    return nutrient
    
    # Fuzzy matching for partial matches
    for nutrient in BLOOD_TEST_RANGES.keys():
        nutrient_words = nutrient.replace('_', ' ').lower().split()
        test_words = test_name_lower.split()
        
        # Check if at least 50% of nutrient words appear in test name
        matches = sum(1 for word in nutrient_words if any(word in test_word for test_word in test_words))
        if matches >= len(nutrient_words) * 0.5:
            if _unit_matches(unit, nutrient):
                return nutrient
    
    return None

def _unit_matches(extracted_unit, nutrient):
    """Check if extracted unit matches expected unit for nutrient"""
    if not extracted_unit or nutrient not in BLOOD_TEST_RANGES:
        return True  # Allow if no unit info
    
    expected_unit = BLOOD_TEST_RANGES[nutrient]['unit'].lower()
    extracted_unit = extracted_unit.lower().strip()
    
    # Direct match
    if expected_unit == extracted_unit:
        return True
    
    # Common unit variations
    unit_variations = {
        'ng/ml': ['ng/ml', 'ngml', 'ng/dl', 'ng per ml', 'ng per dl', 'ng ml', 'ng dl'],
        'pg/ml': ['pg/ml', 'pgml', 'pg/dl', 'pg per ml', 'pg per dl', 'pg ml', 'pg dl'],
        'mcg/dl': ['mcg/dl', 'μg/dl', 'ug/dl', 'mcg per dl', 'mcg dl', 'μg dl', 'ug dl'],
        'mg/dl': ['mg/dl', 'mgdl', 'mg per dl', 'mg dl'],
        'g/dl': ['g/dl', 'gdl', 'g per dl', 'g dl'],
        'meq/l': ['meq/l', 'meql', 'meq per l', 'meq l', 'mequiv/l'],
        'u/l': ['u/l', 'ul', 'units/l', 'unit/l', 'iu/l'],
        'miu/l': ['miu/l', 'miul', 'micro iu/l', 'μiu/l'],
        '%': ['%', 'percent', 'pct'],
        'million/μl': ['million/μl', 'million/ul', 'million/mcl', 'mil/μl', 'x10^6/μl'],
        'thousand/μl': ['thousand/μl', 'thousand/ul', 'k/μl', 'x10^3/μl'],
        'μmol/l': ['μmol/l', 'umol/l', 'micromol/l'],
        'fl': ['fl', 'femtoliters', 'femtoliter'],
        'pg': ['pg', 'picograms', 'picogram']
    }
    
    for standard_unit, variations in unit_variations.items():
        if expected_unit == standard_unit and extracted_unit in variations:
            return True
    
    # Fuzzy matching for common OCR errors
    # Replace common OCR mistakes
    cleaned_extracted = extracted_unit.replace('0', 'o').replace('1', 'l').replace('5', 's')
    if cleaned_extracted in [var.replace('0', 'o').replace('1', 'l').replace('5', 's') 
                           for variations in unit_variations.values() 
                           for var in variations]:
        return True
    
    return False

def _extract_unit_from_context(text, context_parts):
    """Extract unit from text or surrounding context"""
    # First try to find unit in the same text
    unit_match = re.search(r'([a-z/μ]+/[a-z]+|[a-z]+/[a-z]+|μg/dL|ng/mL|pg/mL|mg/dL|g/dL)', text, re.IGNORECASE)
    if unit_match:
        return unit_match.group(1)
    
    # Look in nearby context
    for part in context_parts[:3]:  # Check next few parts
        unit_match = re.search(r'([a-z/μ]+/[a-z]+|[a-z]+/[a-z]+|μg/dL|ng/mL|pg/mL|mg/dL|g/dL)', part, re.IGNORECASE)
        if unit_match:
            return unit_match.group(1)
    
    return None

def _is_reasonable_value(nutrient, value):
    """Check if a blood test value is within reasonable bounds"""
    if not isinstance(value, (int, float)) or value <= 0:
        return False
    
    # Define reasonable bounds for common blood tests
    reasonable_ranges = {
        'vitamin_d': (1, 200),         # ng/mL - very wide range
        'vitamin_b12': (50, 3000),     # pg/mL - very wide range  
        'iron': (10, 500),             # mcg/dL
        'ferritin': (1, 1000),         # ng/mL
        'hemoglobin': (5, 20),         # g/dL
        'glucose': (50, 500),          # mg/dL
        'total_cholesterol': (50, 500), # mg/dL
        'ldl_cholesterol': (20, 300),  # mg/dL
        'hdl_cholesterol': (10, 150),  # mg/dL
        'triglycerides': (30, 1000),   # mg/dL
        'calcium': (5, 15),            # mg/dL
        'magnesium': (0.5, 5),         # mg/dL
        'sodium': (120, 160),          # mEq/L
        'potassium': (2, 8),           # mEq/L
        'tsh': (0.1, 50),              # mIU/L
        'hba1c': (3, 20),              # %
        'folate': (0.5, 50),           # ng/mL
        'crp': (0.1, 100),             # mg/L
        'alt': (5, 500),               # U/L
        'ast': (5, 500),               # U/L
    }
    
    if nutrient in reasonable_ranges:
        min_val, max_val = reasonable_ranges[nutrient]
        return min_val <= value <= max_val
    
    # For unknown nutrients, use very generous bounds
    return 0.01 <= value <= 10000

def _validate_blood_values(blood_values, confidence_scores, text):
    """Validate extracted values and filter out low-confidence results"""
    validated = {}
    
    for nutrient, value in blood_values.items():
        confidence = confidence_scores.get(nutrient, 0)
        
        # Only include values with confidence > 0.4
        if confidence > 0.4:
            # Additional validation: check if the value appears multiple times in text
            value_occurrences = len(re.findall(rf'\b{re.escape(str(value))}\b', text))
            if value_occurrences >= 1:  # Value appears in text
                validated[nutrient] = value
    
    return validated

def get_ai_response(prompt):
    """Get response from OpenAI API"""
    system_prompt = """You are Dr. NutriBot, an expert AI nutritionist with deep knowledge in:
    - Clinical nutrition and biochemistry
    - Blood test interpretation and nutritional deficiency analysis
    - Personalized dietary recommendations
    - Food-nutrient interactions and bioavailability
    - Micronutrient and macronutrient optimization
    - Evidence-based supplement recommendations
    
    Your expertise includes:
    1. Blood Test Analysis: Interpret lab values, identify deficiencies, and understand the clinical significance
    2. Dietary Assessment: Analyze food intake patterns, identify nutritional gaps, and evaluate diet quality
    3. Health Optimization: Address specific health concerns through targeted nutritional interventions
    4. Supplement Guidance: Recommend specific supplements based on evidence and individual needs
    5. Meal Planning: Generate personalized meal plans that address nutritional requirements
    
    Respond in a friendly, conversational manner, explaining complex nutrition concepts in accessible language.
    Provide evidence-based information, focusing on practical advice the person can implement.
    Ask clarifying questions when needed to provide the most accurate and personalized nutrition guidance.
    """
    
    try:
        if use_legacy:
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            return response.choices[0].message.content
        else:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            return response.choices[0].message.content
    except Exception as e:
        return f"Error generating AI response: {str(e)}. Please check your OpenAI API key and try again."

def analyze_blood_test(blood_values, user_profile):
    """Analyze blood test results with AI and return findings"""
    if not blood_values:
        return "No blood test values to analyze."
    
    # Format blood values for prompt
    formatted_values = "\n".join([f"- {k.replace('_', ' ').title()}: {v} {BLOOD_TEST_RANGES[k]['unit']} (Normal range: {BLOOD_TEST_RANGES[k]['normal'][0]}-{BLOOD_TEST_RANGES[k]['normal'][1]} {BLOOD_TEST_RANGES[k]['unit']})" 
                                for k, v in blood_values.items() if k in BLOOD_TEST_RANGES])
    
    # Format user profile
    formatted_profile = "\n".join([f"- {k.replace('_', ' ').title()}: {v}" for k, v in user_profile.items() if v])
    
    prompt = f"""BLOOD TEST ANALYSIS TASK:

I have the following blood test results:
{formatted_values}

User profile:
{formatted_profile}

Please provide a comprehensive analysis including:
1. Identification of any deficiencies or abnormalities - flag any values outside normal range
2. The potential health impacts of these findings
3. Specific dietary recommendations to address each issue
4. Possible supplement recommendations if appropriate
5. Any lifestyle modifications that could help optimize these values

For each deficiency detected, provide:
- Specific foods rich in that nutrient
- How much of these foods should be consumed daily
- What might be causing the deficiency
- Warning signs/symptoms to watch for

Provide your analysis in a clear, structured format with explanations of why these values matter.
"""
    
    return get_ai_response(prompt)


def analyze_diet(dietary_intake, user_profile, blood_values=None):
    """Analyze diet for nutritional gaps and deficiencies"""
    
    # Format user profile
    formatted_profile = "\n".join([f"- {k.replace('_', ' ').title()}: {v}" for k, v in user_profile.items() if v])
    
    # Add blood test context if available
    blood_test_context = ""
    if blood_values:
        blood_test_context = "\n\nBlood Test Results:\n" + "\n".join(
            [f"- {k.replace('_', ' ').title()}: {v} {BLOOD_TEST_RANGES[k]['unit']} (Normal range: {BLOOD_TEST_RANGES[k]['normal'][0]}-{BLOOD_TEST_RANGES[k]['normal'][1]} {BLOOD_TEST_RANGES[k]['unit']})" 
             for k, v in blood_values.items() if k in BLOOD_TEST_RANGES]
        )
    
    prompt = f"""DIET ANALYSIS TASK:

I need a comprehensive analysis of the following diet:

{dietary_intake}

User profile:
{formatted_profile}{blood_test_context}

Please provide:

1. NUTRIENT ANALYSIS:
   - Identify which essential nutrients are MISSING or INSUFFICIENT in this diet
   - For each missing/insufficient nutrient, explain its importance and health consequences of deficiency
   - Flag specifically if the diet lacks nutrients that correspond to any deficiencies in the blood test (if provided)

2. FOOD RECOMMENDATIONS:
   - For each missing nutrient, list 5 specific foods that are rich sources
   - Suggest specific meals that incorporate these foods
   - Note any food combinations that enhance nutrient absorption

3. DIETARY PATTERNS:
   - Identify problematic eating patterns or food choices
   - Suggest practical modifications that address deficiencies while respecting preferences

4. PERSONALIZED ACTION PLAN:
   - Provide a clear, prioritized list of dietary changes
   - Include portion guidance and frequency recommendations

Be specific and practical in your recommendations. Flag any critical deficiencies that require immediate attention.
"""
    
    return get_ai_response(prompt)


def identify_food_nutrient_content(food_item):
    """Analyze a specific food to identify its nutrient content"""
    
    prompt = f"""FOOD NUTRIENT ANALYSIS TASK:

Please analyze this food item: {food_item}

Provide a detailed breakdown of:

1. NUTRITIONAL CONTENT:
   - Major macronutrients (protein, carbs, fats) with approximate amounts per serving
   - Key vitamins and minerals with approximate amounts per serving
   - Indicate whether each amount is low, moderate, or high relative to daily requirements

2. HEALTH BENEFITS:
   - Which specific health conditions or nutritional needs this food addresses
   - Any bioactive compounds with health benefits

3. LIMITATIONS:
   - Which essential nutrients are MISSING or present only in negligible amounts
   - Who should limit or avoid this food (any contraindications)

4. OPTIMIZATION:
   - How to prepare/cook this food to maximize nutrient availability
   - Other foods to pair it with for better nutritional balance

Please be specific about which nutrients are notably ABSENT from this food item.
"""
    
    return get_ai_response(prompt)


def identify_deficiency_foods(nutrient_deficiencies):
    """Identify foods that address specific nutrient deficiencies"""
    
    deficiencies_list = "\n".join([f"- {d}" for d in nutrient_deficiencies])
    
    prompt = f"""NUTRIENT DEFICIENCY FOODS TASK:

I need to address the following nutrient deficiencies through diet:

{deficiencies_list}

For each deficiency, please provide:

1. TOP FOOD SOURCES:
   - List the 10 best food sources for each nutrient, ranked by nutrient density
   - Include both animal and plant sources when applicable
   - Note approximate nutrient content per serving

2. PRACTICAL MEAL IDEAS:
   - 3 breakfast options incorporating these foods
   - 3 lunch options incorporating these foods
   - 3 dinner options incorporating these foods
   - 3 snack options incorporating these foods

3. ABSORPTION FACTORS:
   - Foods or nutrients that enhance absorption
   - Foods or nutrients that inhibit absorption
   - Optimal preparation methods

4. DIETARY PATTERNS:
   - Which overall dietary patterns best address these deficiencies
   - Daily or weekly consumption targets

Please be specific and practical in your recommendations, considering ease of incorporation into typical diets.
"""
    
    return get_ai_response(prompt)

def generate_meal_plan(user_profile, dietary_restrictions, target_nutrients):
    """Generate a personalized meal plan targeting specific nutritional needs"""
    formatted_profile = "\n".join([f"- {k.replace('_', ' ').title()}: {v}" for k, v in user_profile.items() if v])
    
    prompt = f"""MEAL PLAN GENERATION TASK:

Please create a 3-day personalized meal plan for a person with the following profile:
{formatted_profile}

Dietary restrictions/preferences: {dietary_restrictions if dietary_restrictions else "None specified"}

The meal plan should specifically target these nutrients: {', '.join(target_nutrients) if target_nutrients else "general balanced nutrition"}

For each day, include:
1. Breakfast, lunch, dinner, and 2 snacks
2. Approximate calories and macronutrients for each meal
3. Key nutrients provided by each meal, especially those being targeted
4. Simple preparation instructions or time required
5. Shopping list for all ingredients

The meal plan should be realistic, practical, and enjoyable while optimizing nutrition.
"""
    
    return get_ai_response(prompt)

def render_chat_message(message):
    """Render a single chat message with the appropriate styling"""
    if message["role"] == "assistant":
        st.markdown(f"""
        <div class="chat-message bot-message">
            <img src="https://api.dicebear.com/7.x/bottts/svg?seed=healthbot" width="50" height="50" style="border-radius:50%">
            <div class="message-content">
                {message["content"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message user-message">
            <img src="https://api.dicebear.com/7.x/micah/svg?seed=user" width="50" height="50" style="border-radius:50%">
            <div class="message-content">
                {message["content"]}
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_header():
    """Render the main header"""
    st.markdown(f"""
    <div class="main-header">
        <h1>🥗 AI Nutritionist Chat</h1>
        <p>Your personal AI nutritionist for evidence-based guidance and personalized recommendations</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render the sidebar with user profile and document upload"""
    with st.sidebar:
        st.header("👤 Your Profile")
        
        # Basic Information
        st.subheader("Basic Info")
        age = st.number_input("Age", min_value=1, max_value=120, value=30 if st.session_state.user_profile["age"] is None else st.session_state.user_profile["age"], key="sidebar_age")
        gender = st.selectbox("Gender", ["male", "female", "other"], index=0 if st.session_state.user_profile["gender"] is None else ["male", "female", "other"].index(st.session_state.user_profile["gender"]), key="sidebar_gender")
        weight = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, value=70.0 if st.session_state.user_profile["weight"] is None else st.session_state.user_profile["weight"], step=0.5, key="sidebar_weight")
        height = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=170.0 if st.session_state.user_profile["height"] is None else st.session_state.user_profile["height"], step=0.5, key="sidebar_height")
        
        # Activity Level
        activity_level = st.selectbox(
            "Activity Level",
            ["sedentary", "light", "moderate", "active", "very_active"],
            index=2 if st.session_state.user_profile["activity_level"] is None else ["sedentary", "light", "moderate", "active", "very_active"].index(st.session_state.user_profile["activity_level"]),
            key="sidebar_activity"
        )
        
        # Health Information
        st.subheader("Health Info")
        health_conditions = st.text_area("Current Health Conditions", value="" if st.session_state.user_profile["health_conditions"] is None else st.session_state.user_profile["health_conditions"], placeholder="e.g., diabetes, hypertension, etc.", key="sidebar_health_conditions")
        medications = st.text_area("Current Medications", value="" if st.session_state.user_profile["medications"] is None else st.session_state.user_profile["medications"], placeholder="List any medications you're taking", key="sidebar_medications")
        
        # Dietary Preferences
        st.subheader("Dietary Preferences")
        dietary_restrictions = st.multiselect(
            "Dietary Restrictions",
            ["vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free", "low-sodium", "diabetic-friendly"],
            default=[] if st.session_state.user_profile["dietary_restrictions"] is None else st.session_state.user_profile["dietary_restrictions"].split(", ") if st.session_state.user_profile["dietary_restrictions"] else [],
            key="sidebar_dietary_restrictions"
        )
        
        health_goals = st.text_area("Health Goals", value="" if st.session_state.user_profile["health_goals"] is None else st.session_state.user_profile["health_goals"], placeholder="e.g., lose weight, increase energy, improve digestion", key="sidebar_health_goals")
        
        # Update session state when the save button is clicked
        if st.button("💾 Save Profile"):
            st.session_state.user_profile = {
                "age": age,
                "gender": gender,
                "weight": weight,
                "height": height,
                "activity_level": activity_level,
                "health_conditions": health_conditions,
                "medications": medications,
                "dietary_restrictions": ", ".join(dietary_restrictions) if dietary_restrictions else None,
                "health_goals": health_goals
            }
            st.success("Profile saved successfully!")
        
        # Document upload section
        st.header("📄 Document Upload")
        st.info("Upload blood tests or other health documents for analysis")
        
        uploaded_file = st.file_uploader("Upload PDF document", type=["pdf"])
        
        if uploaded_file is not None:
            # Check file size for Streamlit Cloud optimization
            file_size = len(uploaded_file.getvalue())
            is_streamlit_cloud = os.getenv('STREAMLIT_SHARING_MODE') is not None or os.path.exists('/mount/src')
            
            if is_streamlit_cloud and file_size > 10 * 1024 * 1024:  # 10MB limit for cloud
                st.error("❌ File too large for Streamlit Cloud. Please upload a PDF smaller than 10MB.")
                return
            
            # Save uploaded file temporarily with better error handling
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    pdf_path = tmp_file.name
            except Exception as e:
                st.error(f"❌ Error saving uploaded file: {str(e)}")
                return
            
            # Extract text from PDF using enhanced method
            with st.status("Extracting text from PDF...", expanded=True) as status:
                try:
                    text = extract_text_from_pdf(io.BytesIO(uploaded_file.getvalue()))
                    
                    if text.strip():
                        status.update(label="✅ Text extraction successful!", state="complete")
                        word_count = len(text.split())
                        char_count = len(text)
                        
                        # Show cloud-specific info
                        if is_streamlit_cloud:
                            st.info(f"☁️ Running on Streamlit Cloud - Extracted {word_count} words ({char_count:,} characters)")
                        else:
                            st.info(f"📊 Extracted {word_count} words ({char_count:,} characters) from the document")
                    else:
                        status.update(label="⚠️ Text extraction completed with limited results", state="complete")
                        st.warning("Text extraction yielded limited results. The document might be image-based or have formatting issues.")
                except Exception as e:
                    st.error(f"❌ Error during text extraction: {str(e)}")
                    status.update(label="❌ Text extraction failed", state="error")
                    return
            
            # Show document preview
            if text.strip():
                with st.expander("📄 Document Preview", expanded=True):
                    # Show first 500 characters
                    preview_text = text[:500] + ('...' if len(text) > 500 else '')
                    st.text_area("Extracted Text Preview:", value=preview_text, height=150, disabled=True)
                    
                    # Show some statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Words", len(text.split()))
                    with col2:
                        st.metric("Characters", len(text))
                    with col3:
                        pages_detected = text.count("--- Page")
                        st.metric("Pages Detected", pages_detected if pages_detected > 0 else "1")
            else:
                st.error("❌ No text could be extracted from this PDF. Please try a different document or check if the PDF is image-based.")
            
            # Add analyze button
            if st.button("🔍 Analyze Document", disabled=not text.strip()):
                with st.status("Analyzing document with AI...", expanded=True) as status:
                    try:
                        # Environment detection
                        is_streamlit_cloud = os.getenv('STREAMLIT_SHARING_MODE') is not None or os.path.exists('/mount/src')
                        
                        # First, try to extract blood test values from the extracted text
                        blood_values = extract_blood_test_values(text)
                        status.update(label="Extracting blood test values...", state="running")
                        
                        # Use enhanced OCR analysis with the extracted text (cloud-optimized)
                        status.update(label="Running comprehensive document analysis...", state="running")
                        
                        # Only run OCR analysis if no blood values found and file isn't too large
                        if not blood_values and file_size < 5 * 1024 * 1024:  # 5MB limit for OCR on cloud
                            ocr_analysis = analyze_pdf_with_ocr(pdf_path, text)
                        else:
                            ocr_analysis = {
                                "full_text": text,
                                "structured_data": blood_values,
                                "method": "direct_extraction"
                            }
                        
                        # If no blood values found in direct extraction, try OCR results
                        if not blood_values and ocr_analysis.get("structured_data"):
                            blood_values = ocr_analysis["structured_data"]
                            st.info(f"📄 Blood test values found using {ocr_analysis.get('method', 'alternative method')}")
                        
                        # Store results in session state
                        if blood_values:
                            st.session_state.blood_test_results = blood_values
                            status.update(label="Generating AI analysis...", state="running")
                            
                            # Generate AI analysis of blood test results
                            analysis = analyze_blood_test(blood_values, st.session_state.user_profile)
                            
                            # Use enhanced feedback system
                            extraction_method = ocr_analysis.get('method', 'direct extraction')
                            feedback_message = provide_extraction_feedback(text, blood_values, extraction_method)
                            
                            # Add cloud-specific messaging
                            cloud_msg = ""
                            if is_streamlit_cloud:
                                cloud_msg = "\n\n☁️ *Analysis completed on Streamlit Cloud - some advanced features may be limited.*"
                            
                            # Add additional AI analysis
                            full_message = f"""{feedback_message}

**AI Analysis:**
{analysis}{cloud_msg}

💡 *Tip: You can now use the other tools below to analyze your diet and get food recommendations to address any deficiencies.*"""
                            
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": full_message
                            })
                            
                            status.update(label="✅ Analysis complete!", state="complete")
                        else:
                            # Use enhanced feedback system for failed extraction
                            extraction_method = ocr_analysis.get('method', 'text extraction')
                            feedback_message = provide_extraction_feedback(text, blood_values, extraction_method)
                            
                            # Add cloud-specific suggestions
                            if is_streamlit_cloud:
                                feedback_message += "\n\n☁️ **Streamlit Cloud Notes:**\n• Large files may have limited processing\n• OCR capabilities are reduced on the cloud\n• Try smaller, text-based PDFs for best results"
                            
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": feedback_message
                            })
                            
                            status.update(label="✅ Text extracted, but no blood values found", state="complete")
                        
                        # Store the document analysis with memory optimization
                        st.session_state.document_analysis = {
                            "text": text[:10000] if is_streamlit_cloud else text,  # Limit stored text on cloud
                            "ocr_analysis": {
                                "method": ocr_analysis.get("method", "unknown"),
                                "structured_data": blood_values
                            },
                            "blood_values": blood_values,
                            "extraction_successful": bool(text.strip())
                        }
                        
                    except Exception as e:
                        st.error(f"❌ Error during analysis: {str(e)}")
                        if is_streamlit_cloud:
                            st.error("This error might be due to Streamlit Cloud resource limitations. Try a smaller file or simpler PDF.")
                        status.update(label="❌ Analysis failed", state="error")
                    finally:
                        # Clean up temp file - crucial for cloud deployment
                        try:
                            if os.path.exists(pdf_path):
                                os.unlink(pdf_path)
                        except Exception as cleanup_error:
                            st.warning(f"Warning: Could not clean up temporary file: {cleanup_error}")
                        st.rerun()

def render_chat_interface():
    """Render the main chat interface"""
    # Display chat messages
    for message in st.session_state.messages:
        render_chat_message(message)
    
    # Add diet analysis section
    with st.expander("🍎 Diet Analysis Tool", expanded=False):
        st.write("Share your typical daily meals to identify nutritional gaps and get personalized recommendations.")
        
        dietary_intake = st.text_area(
            "Describe your typical daily diet (all meals and snacks for a typical day):",
            placeholder="Example: Breakfast: 2 eggs, toast with butter, coffee with cream\nLunch: Chicken sandwich, apple, chips\nDinner: Pasta with tomato sauce, side salad\nSnacks: Granola bar, yogurt",
            key="diet_analysis_input",
            height=150
        )
        
        if st.button("Analyze My Diet", key="analyze_diet_button"):
            if dietary_intake:
                with st.spinner("Analyzing your diet and identifying nutritional gaps..."):
                    # Check if we have blood test results to correlate with diet
                    blood_values = st.session_state.blood_test_results if hasattr(st.session_state, 'blood_test_results') and st.session_state.blood_test_results else None
                    
                    # Analyze diet and identify nutritional gaps
                    diet_analysis = analyze_diet(dietary_intake, st.session_state.user_profile, blood_values)
                    
                    # Add the analysis to chat
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"🍎 **Diet Analysis Results**\n\nI've analyzed your diet and identified the following:\n\n{diet_analysis}"
                    })
                    st.rerun()
            else:
                st.warning("Please describe your typical daily diet before analyzing.")
    
    # Add food nutrient checker
    with st.expander("🔍 Food Nutrient Checker", expanded=False):
        st.write("Check any food item to see its nutrient content and identify missing nutrients.")
        
        food_item = st.text_input(
            "Enter a food item to analyze:",
            placeholder="Example: avocado, brown rice, salmon, etc.",
            key="food_nutrient_input"
        )
        
        if st.button("Check Nutrients", key="check_nutrients_button"):
            if food_item:
                with st.spinner("Analyzing nutrients in this food..."):
                    # Analyze the food item for nutrient content
                    food_analysis = identify_food_nutrient_content(food_item)
                    
                    # Add the analysis to chat
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"🔍 **Nutrient Analysis: {food_item}**\n\n{food_analysis}"
                    })
                    st.rerun()
            else:
                st.warning("Please enter a food item to analyze.")
    
    # Add deficiency foods tool
    if st.session_state.blood_test_results:
        with st.expander("🥦 Deficiency Foods Finder", expanded=False):
            st.write("Find the best foods to address specific nutrient deficiencies identified in your blood tests.")
            
            # Identify potential deficiencies from blood tests
            potential_deficiencies = []
            for nutrient, value in st.session_state.blood_test_results.items():
                if nutrient in BLOOD_TEST_RANGES and value < BLOOD_TEST_RANGES[nutrient]['normal'][0]:
                    potential_deficiencies.append(nutrient.replace('_', ' ').title())
            
            # Let user select deficiencies to address
            selected_deficiencies = st.multiselect(
                "Select nutrients you want to address:",
                options=potential_deficiencies + ["Vitamin D", "Vitamin B12", "Iron", "Calcium", "Magnesium", "Zinc", "Folate", "Vitamin C", "Omega-3", "Protein"],
                default=potential_deficiencies,
                key="deficiency_selector"
            )
            
            if st.button("Find Foods For These Nutrients", key="find_foods_button"):
                if selected_deficiencies:
                    with st.spinner("Finding the best food sources for these nutrients..."):
                        # Get food recommendations for selected deficiencies
                        food_recommendations = identify_deficiency_foods(selected_deficiencies)
                        
                        # Add the recommendations to chat
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"🥦 **Food Recommendations for {', '.join(selected_deficiencies)}**\n\n{food_recommendations}"
                        })
                        st.rerun()
                else:
                    st.warning("Please select at least one nutrient to address.")
    
    # Chat input
    user_input = st.chat_input("Ask me anything about nutrition, diet, or your health...")
    
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Generate AI response
        with st.spinner("Thinking..."):
            # Check if the message is asking about diet analysis
            diet_analysis_keywords = ["analyze my diet", "what am i missing in my diet", "nutritional gaps", "diet assessment", 
                                      "food diary", "what should i eat", "my meals", "eating habits", "missing nutrients"]
            
            # Check if message contains food item analysis request
            food_analysis_match = re.search(r"(nutrient|nutrients|nutrition|nutritional value|what's in|what is in|analyze)\s+(?:a|an|some|the)?\s+([\w\s]+)", user_input.lower())
            
            # Build context from chat history and user profile
            context = "Chat history:\n"
            for msg in st.session_state.messages[-5:]:  # Last 5 messages for context
                context += f"{msg['role']}: {msg['content']}\n"
            
            context += "\nUser profile:\n"
            for k, v in st.session_state.user_profile.items():
                if v:
                    context += f"{k}: {v}\n"
            
            # Add blood test results if available
            if st.session_state.blood_test_results:
                context += "\nBlood test results:\n"
                for k, v in st.session_state.blood_test_results.items():
                    if k in BLOOD_TEST_RANGES:
                        context += f"{k}: {v} {BLOOD_TEST_RANGES[k]['unit']} (Normal range: {BLOOD_TEST_RANGES[k]['normal'][0]}-{BLOOD_TEST_RANGES[k]['normal'][1]} {BLOOD_TEST_RANGES[k]['unit']})\n"
            
            # Check if this is a diet analysis request
            if any(keyword in user_input.lower() for keyword in diet_analysis_keywords) and len(user_input.split()) > 15:
                # This is likely a diet description, so analyze it
                diet_analysis = analyze_diet(user_input, st.session_state.user_profile, st.session_state.blood_test_results if hasattr(st.session_state, 'blood_test_results') else None)
                ai_response = f"I've analyzed the diet you described:\n\n{diet_analysis}"
            # Check if this is a food item analysis request
            elif food_analysis_match and len(food_analysis_match.group(2).split()) <= 3:
                food_item = food_analysis_match.group(2).strip()
                food_analysis = identify_food_nutrient_content(food_item)
                ai_response = f"Here's my analysis of {food_item}:\n\n{food_analysis}"
            else:
                # Get general AI response
                prompt_instructions = """
Provide a helpful, informative response as Dr. NutriBot. If the user is asking about specific nutrient values or health metrics, reference their profile or blood test data if available.

If the user mentions foods or meals, always identify if any essential nutrients are missing from those foods and suggest complementary foods to provide a complete nutritional profile.

Always flag nutritional deficiencies and make clear connections between blood test results and dietary choices.
"""
                ai_response = get_ai_response(f"{context}\n\nUser's latest message: {user_input}\n{prompt_instructions}")
            
            # Add AI response to chat history
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
        
        # Rerun to update the UI with the new messages
        st.rerun()

def visualize_blood_test_results():
    """Visualize blood test results if available"""
    if st.session_state.blood_test_results:
        with st.expander("📊 View Blood Test Visualization", expanded=False):
            # Create visualization of blood test results
            nutrients = []
            values = []
            statuses = []
            
            for nutrient, value in st.session_state.blood_test_results.items():
                if nutrient in BLOOD_TEST_RANGES:
                    range_info = BLOOD_TEST_RANGES[nutrient]
                    normal_range = range_info["normal"]
                    
                    nutrients.append(nutrient.replace('_', ' ').title())
                    values.append(value)
                    
                    if value < normal_range[0]:
                        statuses.append("Low")
                    elif value > normal_range[1]:
                        statuses.append("High")
                    else:
                        statuses.append("Normal")
            
            if nutrients:
                df = pd.DataFrame({
                    'Nutrient': nutrients,
                    'Value': values,
                    'Status': statuses
                })
                
                # Color mapping for status
                color_map = {'Normal': 'green', 'Low': 'red', 'High': 'orange'}
                df['Color'] = df['Status'].map(color_map)
                
                fig = px.bar(
                    df, 
                    x='Nutrient', 
                    y='Value', 
                    color='Status',
                    color_discrete_map=color_map,
                    title="Blood Test Results Status"
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

def render_onboarding():
    """Render onboarding wizard for new users"""
    if not st.session_state.onboarding_complete:
        st.markdown("""
        <div class="info-box">
            <h3>👋 Welcome to AI Nutritionist Chat!</h3>
            <p>Let's get to know you better so I can provide personalized nutrition guidance.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Multi-step onboarding process
        if st.session_state.current_step == "welcome":
            st.write("### Step 1: Basic Information")
            col1, col2 = st.columns(2)
            
            with col1:
                age = st.number_input("Age", min_value=1, max_value=120, value=30, key="onboarding_age")
                gender = st.selectbox("Gender", ["male", "female", "other"], key="onboarding_gender")
            
            with col2:
                weight = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, value=70.0, step=0.5, key="onboarding_weight")
                height = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=170.0, step=0.5, key="onboarding_height")
            
            if st.button("Continue to Health Information ➡️"):
                st.session_state.user_profile.update({
                    "age": age,
                    "gender": gender,
                    "weight": weight,
                    "height": height
                })
                st.session_state.current_step = "health_info"
                st.rerun()
        
        elif st.session_state.current_step == "health_info":
            st.write("### Step 2: Health Information")
            
            activity_level = st.selectbox(
                "Activity Level",
                ["sedentary", "light", "moderate", "active", "very_active"],
                index=2,
                help="Sedentary: Little to no exercise. Light: Light exercise 1-3 days/week. Moderate: Moderate exercise 3-5 days/week. Active: Hard exercise 6-7 days/week. Very Active: Very hard exercise and physical job or training twice a day.",
                key="onboarding_activity"
            )
            
            health_conditions = st.text_area("Current Health Conditions", placeholder="e.g., diabetes, hypertension, etc.", key="onboarding_health_conditions")
            medications = st.text_area("Current Medications", placeholder="List any medications you're taking", key="onboarding_medications")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Back to Basic Information"):
                    st.session_state.current_step = "welcome"
                    st.rerun()
            
            with col2:
                if st.button("Continue to Dietary Preferences ➡️"):
                    st.session_state.user_profile.update({
                        "activity_level": activity_level,
                        "health_conditions": health_conditions,
                        "medications": medications
                    })
                    st.session_state.current_step = "dietary_preferences"
                    st.rerun()
        
        elif st.session_state.current_step == "dietary_preferences":
            st.write("### Step 3: Dietary Preferences & Goals")
            
            dietary_restrictions = st.multiselect(
                "Dietary Restrictions",
                ["vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free", "low-sodium", "diabetic-friendly"],
                key="onboarding_dietary_restrictions"
            )
            
            health_goals = st.text_area("Health Goals", placeholder="e.g., lose weight, increase energy, improve digestion", key="onboarding_health_goals")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Back to Health Information"):
                    st.session_state.current_step = "health_info"
                    st.rerun()
            
            with col2:
                if st.button("Complete Profile ✅"):
                    st.session_state.user_profile.update({
                        "dietary_restrictions": ", ".join(dietary_restrictions) if dietary_restrictions else None,
                        "health_goals": health_goals
                    })
                    st.session_state.onboarding_complete = True
                    
                    # Add welcome message with personalized info
                    name = "there"
                    gender_term = "person" if st.session_state.user_profile["gender"] == "other" else st.session_state.user_profile["gender"]
                    age = st.session_state.user_profile["age"]
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"""Thanks for sharing your information! Based on what you've told me, I now know you're a {age}-year-old {gender_term} with the following profile:

1. **Activity level**: {st.session_state.user_profile["activity_level"]}
2. **Health conditions**: {st.session_state.user_profile["health_conditions"] if st.session_state.user_profile["health_conditions"] else "None specified"}
3. **Medications**: {st.session_state.user_profile["medications"] if st.session_state.user_profile["medications"] else "None specified"}
4. **Dietary restrictions**: {st.session_state.user_profile["dietary_restrictions"] if st.session_state.user_profile["dietary_restrictions"] else "None specified"}
5. **Health goals**: {st.session_state.user_profile["health_goals"] if st.session_state.user_profile["health_goals"] else "None specified"}

How can I help you today? You can:
- Upload a blood test for me to analyze
- Ask about specific nutritional needs
- Get a personalized meal plan
- Discuss any health or nutrition concerns"""
                    })
                    
                    st.rerun()

def diagnose_extraction_failure(text, blood_values):
    """Diagnose why blood test extraction might have failed and provide helpful feedback"""
    diagnosis = {
        "text_quality": "good",
        "potential_issues": [],
        "suggestions": [],
        "detected_patterns": []
    }
    
    if not text.strip():
        diagnosis["text_quality"] = "no_text"
        diagnosis["potential_issues"].append("No text was extracted from the PDF")
        diagnosis["suggestions"].extend([
            "The PDF might be image-based (scanned document)",
            "Try enabling OCR processing",
            "Ensure the PDF is not password-protected or corrupted"
        ])
        return diagnosis
    
    # Analyze text characteristics
    word_count = len(text.split())
    char_count = len(text)
    line_count = len(text.split('\n'))
    
    if word_count < 50:
        diagnosis["text_quality"] = "insufficient"
        diagnosis["potential_issues"].append(f"Very little text extracted ({word_count} words)")
        diagnosis["suggestions"].append("The PDF might have extraction issues - try OCR processing")
    
    # Look for common blood test indicators
    blood_test_indicators = [
        'lab', 'laboratory', 'test', 'result', 'value', 'level', 'serum', 'plasma',
        'ng/ml', 'mg/dl', 'pg/ml', 'mcg/dl', 'μg/dl', 'g/dl',
        'vitamin', 'iron', 'hemoglobin', 'calcium', 'magnesium'
    ]
    
    found_indicators = [indicator for indicator in blood_test_indicators 
                       if indicator.lower() in text.lower()]
    
    if found_indicators:
        diagnosis["detected_patterns"].extend(found_indicators)
        
        if not blood_values:
            diagnosis["potential_issues"].append("Blood test indicators found but no values extracted")
            diagnosis["suggestions"].extend([
                "The document contains health-related terms but values aren't in standard format",
                "Try manually entering values (e.g., 'My Vitamin D is 25 ng/mL')",
                "Values might be in tables or complex layouts"
            ])
    else:
        diagnosis["potential_issues"].append("No blood test indicators found in text")
        diagnosis["suggestions"].extend([
            "This might not be a blood test report",
            "The document might be a different type of health document",
            "Try uploading a lab report from Quest, LabCorp, or your doctor's office"
        ])
    
    # Look for numbers that could be values
    number_patterns = re.findall(r'\b\d+\.?\d*\b', text)
    if len(number_patterns) > 10:
        diagnosis["detected_patterns"].append(f"Found {len(number_patterns)} numbers in text")
        if not blood_values:
            diagnosis["suggestions"].append("Many numbers found but couldn't match them to blood tests - the format might be non-standard")
    elif len(number_patterns) < 5:
        diagnosis["potential_issues"].append("Very few numbers found in text")
    
    # Check for table-like structures
    if '|' in text or '\t' in text or re.search(r'\s{3,}', text):
        diagnosis["detected_patterns"].append("Table-like structures detected")
        if not blood_values:
            diagnosis["suggestions"].append("Table structure found but values not extracted - might need manual review")
    
    # Check for common lab formatting issues
    if any(char in text for char in ['†', '‡', '*', '§']):
        diagnosis["detected_patterns"].append("Special characters found (footnote markers)")
        diagnosis["suggestions"].append("Document contains footnote markers that might interfere with extraction")
    
    return diagnosis

def provide_extraction_feedback(text, blood_values, extraction_method):
    """Provide user-friendly feedback about extraction results"""
    diagnosis = diagnose_extraction_failure(text, blood_values)
    
    # Create feedback message
    if blood_values:
        feedback = f"""✅ **Extraction Successful!**
        
Found {len(blood_values)} blood test values using {extraction_method}.

**Values Detected:**
{chr(10).join([f"• {k.replace('_', ' ').title()}: {v} {BLOOD_TEST_RANGES[k]['unit']}" 
               for k, v in blood_values.items() if k in BLOOD_TEST_RANGES])}
"""
    else:
        feedback = f"""📄 **Document Analysis Results**

I was able to extract text from your document using {extraction_method}, but couldn't identify specific blood test values in the standard format.

**Diagnosis:**
"""
        
        if diagnosis["potential_issues"]:
            feedback += "\n**Potential Issues:**\n"
            for issue in diagnosis["potential_issues"]:
                feedback += f"• {issue}\n"
        
        if diagnosis["detected_patterns"]:
            feedback += "\n**What I Found:**\n"
            for pattern in diagnosis["detected_patterns"]:
                feedback += f"• {pattern}\n"
        
        if diagnosis["suggestions"]:
            feedback += "\n**Suggestions:**\n"
            for suggestion in diagnosis["suggestions"]:
                feedback += f"• {suggestion}\n"
        
        # Add sample of extracted text if available
        if text.strip():
            text_sample = text[:300] + "..." if len(text) > 300 else text
            feedback += f"""
**Text Sample Extracted:**
```
{text_sample}
```

**What you can do:**
1. **Manual Entry**: Tell me specific values (e.g., "My Vitamin D is 25 ng/mL, Iron is 45 μg/dL")
2. **Ask Questions**: Ask me about specific parts of the document  
3. **Try Different Format**: Upload a clearer PDF if available
"""
    
    return feedback

def main():
    """Main application function"""
    initialize_session_state()
    render_header()
    render_sidebar()
    
    # Main content area
    if not st.session_state.onboarding_complete:
        render_onboarding()
    else:
        # Show blood test visualization if available
        visualize_blood_test_results()
        
        # Show chat interface
        render_chat_interface()

if __name__ == "__main__":
    main()
