"""A simple calculator module with intentional bugs for demonstration."""

import os
import sys
import math
import json  # unused import

# SECURITY ISSUE: Hardcoded credentials
DB_PASSWORD = "admin123"
API_SECRET = "sk-super-secret-key-12345"


# Global mutable state (not ideal)
calculation_history = []


def add(a, b):
    result = a + b
    calculation_history.append(f"{a} + {b} = {result}")
    return result


def subtract(a, b):
    result = a - b
    calculation_history.append(f"{a} - {b} = {result}")
    return result


def multiply(a, b):
    result = a * b
    calculation_history.append(f"{a} * {b} = {result}")
    return result


def divide(a, b):
    # BUG: No zero-division check!
    result = a / b
    calculation_history.append(f"{a} / {b} = {result}")
    return result


def power(base, exp):
    result = base ** exp
    calculation_history.append(f"{base} ^ {exp} = {result}")
    return result


def factorial(n):
    # BUG: No check for negative numbers, will infinite loop
    # BUG: Off-by-one — should start from 1, not 0
    if n == 0:
        return 1
    result = 1
    for i in range(1, n):  # Off-by-one: should be range(1, n+1)
        result *= i
    calculation_history.append(f"{n}! = {result}")
    return result


def batch_calculate(operations, results=[]):
    """Process a list of operations.
    BUG: Mutable default argument!
    """
    func_map = {
        "add": add, "subtract": subtract,
        "multiply": multiply, "divide": divide,
        "power": power, "factorial": factorial,
    }
    for op_name, args in operations:
        try:
            func = func_map.get(op_name)
            if func:
                if isinstance(args, (list, tuple)):
                    results.append(func(*args))
                else:
                    results.append(func(args))
        except:  # BUG: Bare except — catches everything including SystemExit
            results.append(None)
    return results


def smart_calculate(expression):
    """Evaluate a math expression from user input.
    SECURITY BUG: Uses eval() on untrusted input!
    """
    try:
        result = eval(expression)  # DANGEROUS: arbitrary code execution
        return result
    except:
        return None


def get_history():
    return calculation_history


def clear_history():
    global calculation_history
    calculation_history = []


def complex_operation(a, b, c, d, e, f, g, mode):
    """A function with too many parameters and high complexity."""
    result = 0
    if mode == "sum":
        result = a + b + c + d + e + f + g
    elif mode == "product":
        result = a * b * c * d * e * f * g
    elif mode == "weighted":
        if a > 0:
            if b > 0:
                if c > 0:
                    result = (a * 1 + b * 2 + c * 3 + d * 4 + e * 5 + f * 6 + g * 7)
                else:
                    result = (a * 7 + b * 6 + c * 5 + d * 4 + e * 3 + f * 2 + g * 1)
            else:
                if d > 0:
                    result = a + d + g
                else:
                    result = b + e + f
        else:
            if e > 0:
                if f > 0:
                    result = e * f * g
                else:
                    result = a + b + c
            else:
                result = 0
    elif mode == "average":
        result = (a + b + c + d + e + f + g) / 7
    elif mode == "max":
        result = max(a, b, c, d, e, f, g)
    elif mode == "min":
        result = min(a, b, c, d, e, f, g)
    else:
        result = None
    return result
