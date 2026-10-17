"""Configuration: reads settings from the environment / a local .env file.

To switch LLM model, set GEMINI_MODEL in .env. To switch provider entirely,
replace the function in llm.py (the agent only calls the LLM through the
`llm_fn` argument, so nothing else needs to change).
"""
import os

from dotenv import load_dotenv

load_dotenv()  # reads .env in the current folder if it exists

DEFAULT_MODEL = "gemini-3.5-flash"
RECENCY_YEARS = 5          # preferred maximum age of resources (when date is verifiable)
MAX_TOPICS = 8
MIN_TOPICS = 5
RESULTS_PER_TOPIC = 2


def get_api_key():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "your_api_key_here":
        return None
    return key


def get_model_name():
    return os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
