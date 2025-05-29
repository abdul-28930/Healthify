#!/usr/bin/env python3
"""
Streamlit Cloud Entry Point for Healthify AI Nutritionist
Optimized for cloud deployment with resource management
"""

import streamlit as st
import os
import sys

# Set up environment for Streamlit Cloud
def setup_cloud_environment():
    """Setup environment variables and configurations for Streamlit Cloud"""
    
    # Set environment markers for cloud detection
    os.environ['STREAMLIT_CLOUD_MODE'] = '1'
    
    # Memory optimization settings
    os.environ['PYTHONHASHSEED'] = '0'
    
    # Configure matplotlib backend for cloud
    import matplotlib
    matplotlib.use('Agg')

# Initialize cloud environment
setup_cloud_environment()

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import and run the main application
try:
    from chat_nutritionist import main
    
    # Add cloud-specific information to the sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("### ☁️ Streamlit Cloud")
        st.caption("Optimized for cloud deployment")
        st.caption("Memory and processing optimized")
        
        # Show environment info
        if st.checkbox("Show Environment Info", value=False):
            st.write("**Environment Details:**")
            st.write(f"- Python: {sys.version}")
            st.write(f"- Streamlit: {st.__version__}")
            st.write("- Platform: Streamlit Cloud")
            st.write("- OCR: Available (with packages.txt)")
    
    # Run the main application
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    st.error(f"❌ Error importing application: {e}")
    st.info("Please ensure all dependencies are installed correctly.")
except Exception as e:
    st.error(f"❌ Application error: {e}")
    st.info("Please check the logs for more details.") 