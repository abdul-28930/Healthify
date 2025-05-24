# 🥗 AI Nutritionist - Healthify

An intelligent nutrition analysis platform that analyzes blood test reports, evaluates dietary intake, and provides personalized nutritional recommendations using AI.

## 🎯 Features

### 🩸 Blood Test Analysis
- Upload and analyze blood test results
- Identify nutritional deficiencies based on lab values
- Visual representation of results with normal ranges
- Comprehensive AI-powered analysis and recommendations

### 🍽️ Dietary Assessment
- Analyze current diet patterns
- Identify nutritional gaps in meal plans
- Flag foods that don't provide essential nutrients
- Personalized dietary improvement suggestions

### 💬 Health Consultation
- Interactive health questionnaire
- Symptom-based nutritional guidance
- Personalized recommendations for specific health concerns
- Evidence-based nutritional interventions

### 📅 Meal Planning
- Generate personalized meal plans
- Target specific nutrient deficiencies
- Accommodate dietary restrictions and preferences
- Shopping lists and preparation tips

### 📚 Nutrition Education
- Comprehensive nutrient database
- Food source recommendations
- Blood test reference ranges
- Educational content about nutrition

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- OpenAI API key

### Installation

1. **Clone or download the project**
   ```bash
   cd /path/to/Healthify
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **Open your browser**
   Navigate to `http://localhost:8501`

## 🛠️ Configuration

### OpenAI API Setup
1. Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Add it to your `.env` file
3. The app uses GPT-4o-mini for cost-effective, high-quality responses

### Customizing Reference Values
You can modify nutritional reference values in `config.py`:
- Blood test normal ranges
- Daily nutritional requirements
- Gender-specific recommendations

## 📖 Usage Guide

### 1. Set Up Your Profile
- Fill in your basic information in the sidebar
- Include age, gender, weight, height, activity level
- Add health conditions and medications
- Specify dietary restrictions and goals

### 2. Blood Test Analysis
- Enter your recent blood test values
- The app will compare against normal ranges
- Get AI-powered analysis of deficiencies
- Receive specific nutritional recommendations

### 3. Diet Analysis
- Describe your typical meals and snacks
- Answer quick assessment questions
- Get comprehensive dietary evaluation
- Receive improvement suggestions

### 4. Health Consultation
- Describe your health concerns or symptoms
- Use the symptom checklist for guidance
- Get personalized nutritional interventions
- Learn when to seek medical attention

### 5. Meal Planning
- Select nutrients to focus on based on your analysis
- Choose dietary preferences and restrictions
- Generate a 7-day personalized meal plan
- Get shopping lists and preparation tips

## 🔧 Technical Details

### Architecture
- **Frontend**: Streamlit with custom CSS styling
- **AI Engine**: OpenAI GPT-4o-mini with specialized prompts
- **Data Visualization**: Plotly for interactive charts
- **Configuration**: Modular config system

### AI Prompts
The application uses sophisticated prompt engineering:
- **System Prompt**: Establishes AI as expert nutritionist
- **Analysis Prompts**: Structured templates for different analysis types
- **Context Integration**: Combines user profile, blood tests, and dietary data

### Key Components
- `ai_nutritionist.py`: Core AI analysis engine
- `app.py`: Streamlit user interface
- `config.py`: Configuration and reference values
- `requirements.txt`: Python dependencies

## 🔬 Scientific Basis

### Reference Ranges
- Based on standard clinical laboratory ranges
- Gender-specific recommendations
- Age-appropriate guidelines

### Nutritional Guidelines
- FDA daily recommended values
- WHO nutritional guidelines
- Current scientific literature

### AI Training
- Trained on evidence-based nutrition science
- Clinical nutrition protocols
- Food-nutrient interaction knowledge

## ⚠️ Important Disclaimers

- **Educational Purpose Only**: This tool is for educational and informational purposes
- **Not Medical Advice**: Always consult healthcare professionals for medical decisions
- **Blood Test Interpretation**: Lab results should be reviewed by qualified medical professionals
- **Individual Variations**: Nutritional needs vary based on individual factors

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional blood test markers
- More dietary analysis features
- Enhanced meal planning algorithms
- Integration with fitness trackers
- Multi-language support

## 📄 License

This project is for educational and research purposes. Please ensure compliance with OpenAI's usage policies when deploying.

## 🆘 Support

If you encounter issues:
1. Check your OpenAI API key is correctly set
2. Ensure all dependencies are installed
3. Verify Python version compatibility
4. Check the console for error messages

## 🔮 Future Enhancements

- **Food Photo Analysis**: Upload photos for automated nutrition tracking
- **Supplement Recommendations**: Personalized supplement suggestions
- **Progress Tracking**: Monitor nutritional improvements over time
- **Healthcare Integration**: Connect with electronic health records
- **Recipe Generation**: AI-generated recipes based on nutritional needs

---

**🩺 Healthify - Empowering better health through intelligent nutrition analysis** 