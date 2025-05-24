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
    "vitamin_d": {"normal": (30, 100), "unit": "ng/mL"},
    "vitamin_b12": {"normal": (200, 900), "unit": "pg/mL"},
    "iron": {"normal": (60, 170), "unit": "mcg/dL"},
    "ferritin": {"normal": (15, 150), "unit": "ng/mL"},
    "hemoglobin": {"normal": (12.0, 16.0), "unit": "g/dL"},
    "calcium": {"normal": (8.5, 10.5), "unit": "mg/dL"},
    "magnesium": {"normal": (1.7, 2.2), "unit": "mg/dL"},
    "zinc": {"normal": (70, 120), "unit": "mcg/dL"},
    "folate": {"normal": (2.7, 17.0), "unit": "ng/mL"},
} 