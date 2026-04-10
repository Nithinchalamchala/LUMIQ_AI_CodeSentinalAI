"""Utility module with security vulnerabilities for demonstration."""

import pickle
import os


def evaluate_expression(expr):
    """SECURITY BUG: Uses eval() on user input."""
    return eval(expr)


def load_data(raw_bytes):
    """SECURITY BUG: Deserializes untrusted data with pickle."""
    return pickle.loads(raw_bytes)


def get_user_data(user_id):
    """SECURITY BUG: SQL injection vulnerability (simulated)."""
    query = "SELECT * FROM users WHERE id = '" + str(user_id) + "'"
    # In a real app, this would execute the query
    return query


def run_command(cmd):
    """SECURITY BUG: Command injection via os.system."""
    os.system(cmd)


# SECURITY BUG: Hardcoded API key
INTERNAL_API_KEY = "AIzaSyD-FAKE-KEY-1234567890"
DATABASE_URL = "postgresql://admin:password123@prod-server:5432/maindb"


def process_config(config_str):
    """SECURITY BUG: Using exec() to process configuration."""
    exec(config_str)
