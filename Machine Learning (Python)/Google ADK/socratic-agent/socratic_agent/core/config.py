import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("Warning (config.py): GOOGLE_API_KEY not found in .env file. Dependent functionalities might fail.")

# Project Paths
# __file__ is socratic-agent/socratic_agent/core/config.py
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
# socratic-agent/socratic_agent/
SOCRATIC_AGENT_DIR = os.path.dirname(CORE_DIR)
# socratic-agent/
PROJECT_ROOT = os.path.dirname(SOCRATIC_AGENT_DIR)

CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db")
DOCUMENTS_PATH = os.path.join(PROJECT_ROOT, "documents")

# ChromaDB Configuration
COLLECTION_NAME = "socratic_collection"

# Embedding Configuration
EMBEDDING_MODEL = "text-embedding-004" # Google's text-embedding-004 model

# File Handling
DEFAULT_FILE_ENCODING = "latin-1" # Default encoding for reading documents

if __name__ == '__main__':
    print("Config.py loaded. These are the configurations:")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"CHROMA_DB_PATH: {CHROMA_DB_PATH}")
    print(f"DOCUMENTS_PATH: {DOCUMENTS_PATH}")
    print(f"COLLECTION_NAME: {COLLECTION_NAME}")
    print(f"EMBEDDING_MODEL: {EMBEDDING_MODEL}")
    print(f"DEFAULT_FILE_ENCODING: {DEFAULT_FILE_ENCODING}")
    print(f"API_KEY is set: {bool(API_KEY)}") 