"""Configuration management for the Code Review Agent Pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
SAMPLE_PROJECTS_DIR = BASE_DIR / "sample_projects"
TEMP_DIR = Path("/tmp/codesentinel_workspaces")

# --- Local LLM Settings (Ollama) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")

# --- Pipeline Settings ---
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# --- Analysis Settings ---
PYLINT_THRESHOLD = 5.0  # Min score to consider "acceptable"
COMPLEXITY_THRESHOLD = 10  # Max cyclomatic complexity before flagging
BANDIT_SEVERITY = "LOW"  # Minimum severity to report: LOW, MEDIUM, HIGH

# --- Ensure temp directory exists ---
TEMP_DIR.mkdir(parents=True, exist_ok=True)
