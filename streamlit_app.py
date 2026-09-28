"""Streamlit Cloud/Replit entry point.

The main application remains in app.py so existing imports and workflows keep
working. This wrapper lets Streamlit deployments use the conventional
streamlit_app.py main-file path.
"""

from app import main


if __name__ == "__main__":
    main()