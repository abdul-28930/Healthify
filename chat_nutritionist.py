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
    # Initialize OCR-related resources if needed
    return True

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
    """Extract text from uploaded PDF file"""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page_num].extract_text()
    return text

def analyze_pdf_with_ocr(pdf_path):
    """Analyze PDF document using OCR"""
    try:
        # Ensure OCR is setup
        setup_ocr()
        
        # Convert PDF to images for OCR processing
        images = convert_from_path(pdf_path)
        extracted_text = ""
        
        for i, image in enumerate(images):
            # Extract text using OCR
            page_text = pytesseract.image_to_string(image)
            extracted_text += f"\n--- Page {i+1} ---\n{page_text}"
        
        # Extract structured information
        # Look for patterns like "Test: Value Unit" or "Test Value Unit"
        test_results = {}
        
        # Common blood test patterns
        patterns = [
            # Pattern: Test Name: 123 units
            r'([A-Za-z\s]+):\s*(\d+\.?\d*)\s*([A-Za-z/%]+)',
            # Pattern: Test Name 123 units
            r'([A-Za-z\s]+)\s+(\d+\.?\d*)\s*([A-Za-z/%]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, extracted_text)
            for match in matches:
                test_name = match[0].strip().lower()
                value = float(match[1])
                unit = match[2]
                
                test_results[test_name] = {
                    "value": value,
                    "unit": unit
                }
        
        return {
            "full_text": extracted_text,
            "structured_data": test_results
        }
    except Exception as e:
        st.error(f"Error analyzing document with OCR: {str(e)}")
        return {
            "full_text": "",
            "structured_data": {}
        }

def extract_blood_test_values(text):
    """Extract blood test values from document text"""
    blood_values = {}
    
    # Pattern matching for common blood test formats
    for nutrient, info in BLOOD_TEST_RANGES.items():
        # Convert to regular form for regex
        nutrient_regex = nutrient.replace('_', ' ')
        # Look for patterns like "Vitamin D: 30 ng/mL" or "Vitamin D 30 ng/mL"
        pattern = rf"(?i){nutrient_regex}[:|\s]{{1,3}}(\d+\.?\d*)\s*{info['unit']}"
        match = re.search(pattern, text)
        
        if match:
            try:
                blood_values[nutrient] = float(match.group(1))
            except (ValueError, IndexError):
                continue
    
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
            
            # Extract text from PDF
            text = extract_text_from_pdf(io.BytesIO(uploaded_file.getvalue()))
            
            # Show document preview
            st.markdown(f"""
            <div class="document-preview">
                <h4>📄 Document Preview</h4>
                <p>{text[:300]}{'...' if len(text) > 300 else ''}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Add analyze button
            if st.button("🔍 Analyze Document"):
                with st.spinner("Analyzing document with advanced AI..."):
                    # Extract blood test values
                    blood_values = extract_blood_test_values(text)
                    
                    # Use OCR for document analysis
                    ocr_analysis = analyze_pdf_with_ocr(pdf_path)
                    
                    # Store results in session state
                    if blood_values:
                        st.session_state.blood_test_results = blood_values
                        
                        # Generate AI analysis of blood test results
                        analysis = analyze_blood_test(blood_values, st.session_state.user_profile)
                        
                        # Create the blood test values formatted text outside the f-string
                        formatted_blood_values = ""
                        for k, v in blood_values.items():
                            if k in BLOOD_TEST_RANGES:
                                nutrient_name = k.replace('_', ' ').title()
                                unit = BLOOD_TEST_RANGES[k]["unit"]
                                low_range = BLOOD_TEST_RANGES[k]["normal"][0]
                                high_range = BLOOD_TEST_RANGES[k]["normal"][1]
                                formatted_blood_values += f"- **{nutrient_name}**: {v} {unit} (Normal range: {low_range}-{high_range} {unit})\n"
                        
                        # Now use the pre-formatted text in the f-string
                        message_content = f"""📊 **Blood Test Analysis Results**\n\nI've analyzed your blood test document and found the following values:\n\n{formatted_blood_values}\n\n{analysis}"""
                        
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": message_content
                        })
                    else:
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": "I couldn't extract specific blood test values from your document. Could you provide the values manually or upload a clearer document?"
                        })
                    
                    # Store the document analysis
                    st.session_state.document_analysis = {
                        "text": text,
                        "ocr_analysis": ocr_analysis,
                        "blood_values": blood_values
                    }
                    
                    # Clean up temp file
                    os.unlink(pdf_path)
                    st.experimental_rerun()

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
                    st.experimental_rerun()
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
                    st.experimental_rerun()
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
                        st.experimental_rerun()
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
        st.experimental_rerun()

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
                st.experimental_rerun()
        
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
                    st.experimental_rerun()
            
            with col2:
                if st.button("Continue to Dietary Preferences ➡️"):
                    st.session_state.user_profile.update({
                        "activity_level": activity_level,
                        "health_conditions": health_conditions,
                        "medications": medications
                    })
                    st.session_state.current_step = "dietary_preferences"
                    st.experimental_rerun()
        
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
                    st.experimental_rerun()
            
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
                    
                    st.experimental_rerun()

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
