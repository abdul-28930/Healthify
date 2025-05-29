import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"

# Application Configuration
APP_TITLE = "AI Nutritionist - Healthify"
APP_DESCRIPTION = "Intelligent nutrition analysis and personalized recommendations"

# Nutritional Reference Values (Daily Recommended Intake)
DAILY_NUTRITION_REQUIREMENTS = {
    "adult_male": {
        "calories": 2500,
        "protein": 56,  # grams
        "vitamin_d": 15,  # mcg
        "vitamin_b12": 2.4,  # mcg
        "iron": 8,  # mg
        "calcium": 1000,  # mg
        "magnesium": 400,  # mg
        "zinc": 11,  # mg
        "folate": 400,  # mcg
        "vitamin_c": 90,  # mg
        "omega_3": 1.6,  # grams
    },
    "adult_female": {
        "calories": 2000,
        "protein": 46,  # grams
        "vitamin_d": 15,  # mcg
        "vitamin_b12": 2.4,  # mcg
        "iron": 18,  # mg
        "calcium": 1000,  # mg
        "magnesium": 310,  # mg
        "zinc": 8,  # mg
        "folate": 400,  # mcg
        "vitamin_c": 75,  # mg
        "omega_3": 1.1,  # grams
    }
}

# Blood Test Normal Ranges
BLOOD_TEST_RANGES = {
    # Vitamins
    "vitamin_d": {"normal": (30, 100), "unit": "ng/mL"},
    "vitamin_b12": {"normal": (200, 900), "unit": "pg/mL"},
    "folate": {"normal": (2.7, 17.0), "unit": "ng/mL"},
    "vitamin_c": {"normal": (0.4, 2.0), "unit": "mg/dL"},
    "vitamin_a": {"normal": (30, 65), "unit": "μg/dL"},
    "vitamin_e": {"normal": (5.5, 17.0), "unit": "mg/L"},
    
    # Minerals and Trace Elements
    "iron": {"normal": (60, 170), "unit": "mcg/dL"},
    "ferritin": {"normal": (15, 150), "unit": "ng/mL"},
    "transferrin_saturation": {"normal": (20, 50), "unit": "%"},
    "calcium": {"normal": (8.5, 10.5), "unit": "mg/dL"},
    "magnesium": {"normal": (1.7, 2.2), "unit": "mg/dL"},
    "zinc": {"normal": (70, 120), "unit": "mcg/dL"},
    "copper": {"normal": (70, 140), "unit": "mcg/dL"},
    "selenium": {"normal": (70, 150), "unit": "ng/mL"},
    
    # Blood Chemistry
    "hemoglobin": {"normal": (12.0, 16.0), "unit": "g/dL"},
    "hematocrit": {"normal": (36, 48), "unit": "%"},
    "mch": {"normal": (27, 33), "unit": "pg"},
    "mcv": {"normal": (80, 100), "unit": "fL"},
    "mchc": {"normal": (32, 36), "unit": "g/dL"},
    "rbc": {"normal": (4.2, 5.4), "unit": "million/μL"},
    "wbc": {"normal": (4.5, 11.0), "unit": "thousand/μL"},
    "platelets": {"normal": (150, 400), "unit": "thousand/μL"},
    
    # Metabolic Panel
    "glucose": {"normal": (70, 100), "unit": "mg/dL"},
    "hba1c": {"normal": (4.0, 5.6), "unit": "%"},
    "creatinine": {"normal": (0.6, 1.2), "unit": "mg/dL"},
    "bun": {"normal": (7, 20), "unit": "mg/dL"},
    "sodium": {"normal": (136, 145), "unit": "mEq/L"},
    "potassium": {"normal": (3.5, 5.0), "unit": "mEq/L"},
    "chloride": {"normal": (98, 107), "unit": "mEq/L"},
    "co2": {"normal": (22, 29), "unit": "mEq/L"},
    
    # Lipid Panel
    "total_cholesterol": {"normal": (100, 200), "unit": "mg/dL"},
    "ldl_cholesterol": {"normal": (0, 100), "unit": "mg/dL"},
    "hdl_cholesterol": {"normal": (40, 60), "unit": "mg/dL"},
    "triglycerides": {"normal": (0, 150), "unit": "mg/dL"},
    
    # Liver Function
    "alt": {"normal": (7, 35), "unit": "U/L"},
    "ast": {"normal": (8, 40), "unit": "U/L"},
    "alkaline_phosphatase": {"normal": (44, 147), "unit": "U/L"},
    "bilirubin_total": {"normal": (0.3, 1.2), "unit": "mg/dL"},
    "albumin": {"normal": (3.5, 5.0), "unit": "g/dL"},
    "total_protein": {"normal": (6.3, 8.2), "unit": "g/dL"},
    
    # Thyroid Function
    "tsh": {"normal": (0.4, 4.0), "unit": "mIU/L"},
    "t4_free": {"normal": (0.8, 1.8), "unit": "ng/dL"},
    "t3_free": {"normal": (2.3, 4.2), "unit": "pg/mL"},
    
    # Inflammatory Markers
    "crp": {"normal": (0, 3.0), "unit": "mg/L"},
    "esr": {"normal": (0, 30), "unit": "mm/hr"},
    
    # Hormones
    "testosterone": {"normal": (300, 1000), "unit": "ng/dL"},
    "estradiol": {"normal": (30, 400), "unit": "pg/mL"},
    "cortisol": {"normal": (6, 23), "unit": "mcg/dL"},
    "insulin": {"normal": (2, 25), "unit": "μU/mL"},
    
    # Other Important Markers
    "homocysteine": {"normal": (4, 15), "unit": "μmol/L"},
    "uric_acid": {"normal": (3.4, 7.0), "unit": "mg/dL"},
    "phosphorus": {"normal": (2.5, 4.5), "unit": "mg/dL"}
} 