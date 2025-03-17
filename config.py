import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Read the API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
