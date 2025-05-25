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
    """Initialize OCR-related resources"""
    try:
        # Set Tesseract path
        tesseract_cmd = None
        
        # Check common Tesseract paths
        possible_paths = [
            '/usr/bin/tesseract',  # Linux/Streamlit Cloud
            '/usr/local/bin/tesseract',  # Some Linux/Mac
            'C:/Program Files/Tesseract-OCR/tesseract.exe',  # Windows
            'C:/Program Files (x86)/Tesseract-OCR/tesseract.exe'  # Windows (32-bit)
        ]
        
        # Try to find Tesseract in common locations
        for path in possible_paths:
            if os.path.exists(path):
                tesseract_cmd = path
                break
        
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Test Tesseract installation
        pytesseract.get_tesseract_version()
        return True
    except Exception as e:
        st.warning(f"Tesseract OCR is not properly installed or not in PATH. Some features may be limited. Error: {str(e)}")
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
    """Enhanced PDF document analysis with OCR fallback"""
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
        
        # Try to set up OCR as fallback
        ocr_available = setup_ocr()
        
        # Try direct extraction methods first
        try:
            with open(pdf_path, 'rb') as file:
                # Try pdfplumber
                try:
                    with pdfplumber.open(file) as pdf:
                        direct_text = ""
                        for page_num, page in enumerate(pdf.pages):
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
                
                # Try PyMuPDF
                try:
                    file.seek(0)
                    pdf_bytes = file.read()
                    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                    
                    direct_text = ""
                    for page_num in range(pdf_document.page_count):
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
        
        # If direct extraction failed, try OCR if available
        if ocr_available:
            try:
                st.info("🔍 Attempting OCR analysis (this may take longer)...")
                
                # Detect if we're on Streamlit Cloud
                poppler_path = '/usr/bin' if os.path.exists('/usr/bin/pdftoppm') else None
                
                # Convert PDF to images for OCR processing
                images = convert_from_path(pdf_path, poppler_path=poppler_path, first_page=1, last_page=3)  # Limit to first 3 pages
                ocr_text = ""
                
                for i, image in enumerate(images):
                    try:
                        # Convert image to grayscale for better OCR results
                        gray_image = image.convert('L')
                        # Use custom OCR config for better results
                        custom_config = r'--oem 3 --psm 6'
                        page_text = pytesseract.image_to_string(gray_image, config=custom_config)
                        ocr_text += f"\n--- Page {i+1} (OCR) ---\n{page_text}"
                    except Exception as e:
                        st.warning(f"Error processing page {i+1} with OCR: {str(e)}")
                        continue
                
                if ocr_text.strip():
                    # Extract structured information
                    test_results = extract_blood_test_values(ocr_text)
                    
                    return {
                        "full_text": ocr_text,
                        "structured_data": test_results,
                        "method": "OCR"
                    }
                
            except Exception as e:
                st.warning(f"OCR processing failed: {str(e)}")
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
        st.error(f"Unexpected error in document analysis: {str(e)}")
        return {
            "full_text": "",
            "structured_data": {},
            "error": str(e),
            "method": "error"
        }

def extract_blood_test_values(text):
    """Enhanced extraction of blood test values from document text"""
    blood_values = {}
    
    # Clean up the text for better matching
    cleaned_text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    
    # Pattern matching for common blood test formats
    for nutrient, info in BLOOD_TEST_RANGES.items():
        # Convert to regular form for regex and create variations
        nutrient_name = nutrient.replace('_', ' ')
        nutrient_variations = [
            nutrient_name,
            nutrient_name.replace(' ', ''),  # No spaces
            nutrient_name.replace(' ', '_'),  # Underscores
            nutrient_name.replace(' ', '-'),  # Hyphens
        ]
        
        # Add common aliases
        if 'vitamin_d' in nutrient.lower():
            nutrient_variations.extend(['25(OH)D', '25-hydroxyvitamin D', 'Vit D', 'VitD'])
        elif 'vitamin_b12' in nutrient.lower():
            nutrient_variations.extend(['B12', 'Cobalamin', 'Vit B12'])
        elif 'folate' in nutrient.lower():
            nutrient_variations.extend(['Folic Acid', 'Vitamin B9', 'B9'])
        elif 'iron' in nutrient.lower():
            nutrient_variations.extend(['Fe', 'Serum Iron'])
        
        # Try different patterns for each variation
        for variation in nutrient_variations:
            patterns = [
                # Standard format: "Vitamin D: 30 ng/mL"
                rf"(?i){re.escape(variation)}\s*[:=]\s*(\d+\.?\d*)\s*{re.escape(info['unit'])}",
                # Space format: "Vitamin D 30 ng/mL"
                rf"(?i){re.escape(variation)}\s+(\d+\.?\d*)\s*{re.escape(info['unit'])}",
                # Reverse format: "30 ng/mL Vitamin D"
                rf"(?i)(\d+\.?\d*)\s*{re.escape(info['unit'])}\s+{re.escape(variation)}",
                # Table format: "Vitamin D | 30 | ng/mL"
                rf"(?i){re.escape(variation)}\s*[|]\s*(\d+\.?\d*)\s*[|]?\s*{re.escape(info['unit'])}",
                # Flexible separators
                rf"(?i){re.escape(variation)}\s*[-–—]\s*(\d+\.?\d*)\s*{re.escape(info['unit'])}",
                # Without units (assume correct unit)
                rf"(?i){re.escape(variation)}\s*[:=]\s*(\d+\.?\d*)",
                rf"(?i){re.escape(variation)}\s+(\d+\.?\d*)\s*$",
            ]
            
            for pattern in patterns:
                match = re.search(pattern, cleaned_text)
                if match:
                    try:
                        value = float(match.group(1))
                        # Validate that the value is reasonable
                        if 0.1 <= value <= 10000:  # Basic sanity check
                            blood_values[nutrient] = value
                            break  # Found a match, move to next nutrient
                    except (ValueError, IndexError):
                        continue
            
            if nutrient in blood_values:
                break  # Found a match, move to next nutrient
    
    # Additional pattern for common formats without predefined nutrients
    general_patterns = [
        r'([A-Za-z\s\d\(\)]+?)\s*[:=]\s*(\d+\.?\d*)\s*(mg/dL|ng/mL|μg/dL|mcg/L|IU/L|pg/mL|nmol/L)',
        r'([A-Za-z\s\d\(\)]+?)\s+(\d+\.?\d*)\s+(mg/dL|ng/mL|μg/dL|mcg/L|IU/L|pg/mL|nmol/L)',
    ]
    
    for pattern in general_patterns:
        matches = re.finditer(pattern, cleaned_text, re.IGNORECASE)
        for match in matches:
            test_name = match.group(1).strip()
            value = match.group(2)
            unit = match.group(3)
            
            # Try to match to known nutrients
            for nutrient, info in BLOOD_TEST_RANGES.items():
                nutrient_name = nutrient.replace('_', ' ').lower()
                if nutrient_name in test_name.lower() and info['unit'].lower() == unit.lower():
                    try:
                        blood_values[nutrient] = float(value)
                    except ValueError:
                        pass
    
    return blood_values

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
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                pdf_path = tmp_file.name
            
            # Extract text from PDF using enhanced method
            with st.status("Extracting text from PDF...", expanded=True) as status:
                text = extract_text_from_pdf(io.BytesIO(uploaded_file.getvalue()))
                
                if text.strip():
                    status.update(label="✅ Text extraction successful!", state="complete")
                    word_count = len(text.split())
                    char_count = len(text)
                    st.info(f"📊 Extracted {word_count} words ({char_count} characters) from the document")
                else:
                    status.update(label="⚠️ Text extraction completed with limited results", state="complete")
                    st.warning("Text extraction yielded limited results. The document might be image-based or have formatting issues.")
            
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
                        # First, try to extract blood test values from the extracted text
                        blood_values = extract_blood_test_values(text)
                        status.update(label="Extracting blood test values...", state="running")
                        
                        # Use enhanced OCR analysis with the extracted text
                        status.update(label="Running comprehensive document analysis...", state="running")
                        ocr_analysis = analyze_pdf_with_ocr(pdf_path, text)
                        
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
                            
                            # Create the blood test values formatted text
                            formatted_blood_values = ""
                            deficiency_count = 0
                            for k, v in blood_values.items():
                                if k in BLOOD_TEST_RANGES:
                                    nutrient_name = k.replace('_', ' ').title()
                                    unit = BLOOD_TEST_RANGES[k]["unit"]
                                    low_range = BLOOD_TEST_RANGES[k]["normal"][0]
                                    high_range = BLOOD_TEST_RANGES[k]["normal"][1]
                                    
                                    # Check if value is out of range
                                    if v < low_range:
                                        status_icon = "🔴"
                                        deficiency_count += 1
                                    elif v > high_range:
                                        status_icon = "🟠"
                                    else:
                                        status_icon = "🟢"
                                    
                                    formatted_blood_values += f"{status_icon} **{nutrient_name}**: {v} {unit} (Normal: {low_range}-{high_range} {unit})\n"
                            
                            # Success message with summary
                            success_summary = f"Found {len(blood_values)} blood test values"
                            if deficiency_count > 0:
                                success_summary += f" with {deficiency_count} potential deficiencies detected"
                            
                            message_content = f"""📊 **Blood Test Analysis Results**

{success_summary}

**Extracted Values:**
{formatted_blood_values}

**AI Analysis:**
{analysis}

💡 *Tip: You can now use the other tools below to analyze your diet and get food recommendations to address any deficiencies.*"""
                            
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": message_content
                            })
                            
                            status.update(label="✅ Analysis complete!", state="complete")
                        else:
                            # No blood values found
                            text_sample = text[:200] + "..." if len(text) > 200 else text
                            
                            message_content = f"""📄 **Document Analysis Results**

I was able to extract text from your document, but couldn't identify specific blood test values in the standard format.

**Text Sample Extracted:**
```
{text_sample}
```

**What you can do:**
1. **Manual Entry**: If this contains blood test results, you can tell me the values manually (e.g., "My Vitamin D is 25 ng/mL, Iron is 45 μg/dL")
2. **Ask Questions**: You can ask me about specific parts of the document
3. **Try Another Format**: Upload a clearer PDF or different format if available

Feel free to share specific values or ask me anything about nutrition and health! 😊"""
                            
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": message_content
                            })
                            
                            status.update(label="✅ Text extracted, but no blood values found", state="complete")
                        
                        # Store the document analysis
                        st.session_state.document_analysis = {
                            "text": text,
                            "ocr_analysis": ocr_analysis,
                            "blood_values": blood_values,
                            "extraction_successful": bool(text.strip())
                        }
                        
                    except Exception as e:
                        st.error(f"❌ Error during analysis: {str(e)}")
                        status.update(label="❌ Analysis failed", state="error")
                    finally:
                        # Clean up temp file
                        try:
                            os.unlink(pdf_path)
                        except:
                            pass  # Ignore cleanup errors
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
