"""Fixer Agent — autonomously implements code fixes."""

from __future__ import annotations
import os
import json
from typing import Any, Optional, Callable

from backend.agents.base_agent import BaseAgent
from backend.models import (
    AgentType, Issue, FixPlan, FixAction,
    CodeChange, FixResult
)
from backend.tools.git_tools import GitTools


class FixerAgent(BaseAgent):
    """
    Agent 3: Implements code fixes autonomously.

    For each fix action in the plan:
    1. Reads the target file
    2. Uses Claude to generate the fix
    3. Applies the change
    4. Records the before/after diff
    """

    def __init__(self, event_callback: Optional[Callable] = None):
        super().__init__(event_callback)
        self.git_tools = GitTools()

    @property
    def agent_type(self) -> AgentType:
        return AgentType.FIXER

    @property
    def name(self) -> str:
        return "Fixer Agent"

    @property
    def system_prompt(self) -> str:
        return (
            "You are an expert Python developer who fixes code issues. "
            "Given the original code and an issue to fix, you produce the corrected "
            "version of the ENTIRE file. You make minimal, targeted changes. "
            "You preserve the original code structure and style. "
            "You ONLY return the fixed code, nothing else — no explanations, "
            "no markdown, just the Python code."
        )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Apply fixes based on the plan.

        Context keys:
            - fix_plan: dict — the fix plan from the Planner
            - issues: list[dict] — original issues
            - target_path: str — project path
            - verification_feedback: str — feedback from previous verification (retry)
        """
        plan_data = context.get("fix_plan", {})
        fix_plan = FixPlan(**plan_data) if isinstance(plan_data, dict) else plan_data
        target_path = context.get("target_path", "")
        raw_issues = context.get("issues", [])
        feedback = context.get("verification_feedback", "")

        issues_map = {}
        for raw in raw_issues:
            issue = Issue(**raw) if isinstance(raw, dict) else raw
            issues_map[issue.id] = issue

        await self.emit_event("started", "Starting code fixes",
                              f"Applying {len(fix_plan.actions)} fixes"
                              + (f" (retry with feedback)" if feedback else ""))

        changes: list[CodeChange] = []
        succeeded = 0
        failed = 0

        # Group actions by file to apply changes coherently
        by_file: dict[str, list[FixAction]] = {}
        for action in fix_plan.actions:
            by_file.setdefault(action.file_path, []).append(action)

        for file_path, file_actions in by_file.items():
            full_path = file_path
            if not os.path.isabs(file_path):
                full_path = os.path.join(target_path, file_path)

            if not os.path.exists(full_path):
                await self.emit_event("error", f"File not found: {file_path}")
                failed += len(file_actions)
                continue

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    original_code = f.read()
            except IOError as e:
                await self.emit_event("error", f"Cannot read {file_path}: {e}")
                failed += len(file_actions)
                continue

            # Build fix prompt for all issues in this file
            issue_details = []
            for action in file_actions:
                issue = issues_map.get(action.issue_id)
                if issue:
                    issue_details.append({
                        "line": issue.line_number,
                        "title": issue.title,
                        "description": issue.description,
                        "approach": action.approach
                    })

            await self.emit_event("tool_use", f"Fixing {os.path.basename(file_path)}",
                                  f"Applying {len(issue_details)} fixes")

            fix_prompt = self._build_fix_prompt(
                original_code, issue_details, file_path, feedback
            )
            fixed_code = await self._call_llm(fix_prompt, max_tokens=8192)

            # Clean up LLM response (remove markdown fences if present)
            fixed_code = self._clean_code_response(fixed_code)

            # Validate the fix
            if not fixed_code.strip() or fixed_code.strip() == original_code.strip():
                await self.emit_event("error", f"No changes produced for {file_path}")
                failed += len(file_actions)
                continue

            # Verify syntax
            try:
                compile(fixed_code, file_path, 'exec')
            except SyntaxError as e:
                await self.emit_event("error",
                                      f"Fix produced invalid syntax in {file_path}: {e}")
                failed += len(file_actions)
                continue

            # Apply the fix
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                succeeded += len(file_actions)
            except IOError as e:
                await self.emit_event("error", f"Cannot write {file_path}: {e}")
                failed += len(file_actions)
                continue

            # Generate diff
            diff = self.git_tools.generate_diff(original_code, fixed_code, file_path)

            change = CodeChange(
                file_path=file_path,
                original_code=original_code,
                fixed_code=fixed_code,
                diff=diff,
                issue_id=", ".join(a.issue_id for a in file_actions),
                description=f"Fixed {len(file_actions)} issue(s): " +
                            ", ".join(a.approach[:50] for a in file_actions),
                success=True
            )
            changes.append(change)

            await self.emit_event("result", f"Fixed {os.path.basename(file_path)}",
                                  f"{len(file_actions)} issues fixed")

        result = FixResult(
            changes=changes,
            total_attempted=succeeded + failed,
            total_succeeded=succeeded,
            total_failed=failed,
            summary=f"Applied {succeeded} fixes, {failed} failed out of {succeeded + failed} total."
        )

        await self.emit_event("result", f"Fixing complete: {succeeded} succeeded, {failed} failed",
                              result.summary)

        return {"fix_result": result.model_dump()}

    def _build_fix_prompt(self, code: str, issues: list[dict],
                          file_path: str, feedback: str = "") -> str:
        """Build a prompt to fix all issues in a file."""
        issues_text = "\n".join([
            f"  Line {i['line']}: {i['title']} — {i['description']}\n"
            f"    Fix approach: {i['approach']}"
            for i in issues
        ])

        prompt = f"""Fix the following Python code issues. Return the COMPLETE fixed file.

File: {file_path}

Issues to fix:
{issues_text}
"""
        if feedback:
            prompt += f"""
IMPORTANT — Previous fix attempt failed verification:
{feedback}
Please fix these additional problems.
"""

        prompt += f"""
Original code:
```python
{code}
```

Return ONLY the complete fixed Python code. No explanations, no markdown fences, just code."""

        return prompt

    def _clean_code_response(self, response: str) -> str:
        """Remove markdown code fences from LLM response."""
        text = response.strip()
        if text.startswith("```python"):
            text = text[9:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip() + "\n"

    def _get_demo_response(self, prompt: str) -> str:
        """Demo mode: return fixed code for the buggy calculator."""
        if "calculator" in prompt.lower():
            return '''"""A calculator module with proper error handling."""

import math


# Calculation history
_history = []


def add(a, b):
    """Add two numbers."""
    result = float(a) + float(b)
    _history.append(f"{a} + {b} = {result}")
    return result


def subtract(a, b):
    """Subtract b from a."""
    result = float(a) - float(b)
    _history.append(f"{a} - {b} = {result}")
    return result


def multiply(a, b):
    """Multiply two numbers."""
    result = float(a) * float(b)
    _history.append(f"{a} * {b} = {result}")
    return result


def divide(a, b):
    """Divide a by b with zero-division check."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    result = float(a) / float(b)
    _history.append(f"{a} / {b} = {result}")
    return result


def power(base, exponent):
    """Raise base to the power of exponent."""
    result = math.pow(float(base), float(exponent))
    _history.append(f"{base} ^ {exponent} = {result}")
    return result


def factorial(n):
    """Calculate factorial of n."""
    n = int(n)
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    _history.append(f"{n}! = {result}")
    return result


def batch_calculate(operations):
    """Process a list of operations. Each operation is (func_name, args).

    Args:
        operations: List of tuples (function_name, arguments)

    Returns:
        List of results
    """
    if operations is None:
        operations = []
    results = []
    func_map = {
        "add": add, "subtract": subtract,
        "multiply": multiply, "divide": divide,
        "power": power, "factorial": factorial,
    }
    for op_name, args in operations:
        func = func_map.get(op_name)
        if func is None:
            results.append(f"Unknown operation: {op_name}")
            continue
        try:
            if isinstance(args, (list, tuple)):
                results.append(func(*args))
            else:
                results.append(func(args))
        except Exception as e:
            results.append(f"Error in {op_name}: {e}")
    return results


def get_history():
    """Return calculation history."""
    return list(_history)


def clear_history():
    """Clear calculation history."""
    _history.clear()
'''
        elif "utils" in prompt.lower():
            return '''"""Utility functions with safe implementations."""

import ast
import json
import hashlib
import os


def safe_evaluate(expression: str):
    """Safely evaluate a mathematical expression.

    Uses ast.literal_eval for safe evaluation instead of eval().
    """
    try:
        return ast.literal_eval(expression)
    except (ValueError, SyntaxError):
        raise ValueError(f"Cannot safely evaluate expression: {expression}")


def load_config(config_path: str) -> dict:
    """Load configuration from a JSON file.

    Args:
        config_path: Path to the JSON config file

    Returns:
        Dictionary of config values
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def hash_data(data: str) -> str:
    """Create a SHA-256 hash of input data.

    Args:
        data: String data to hash

    Returns:
        Hex digest of the hash
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def sanitize_input(user_input: str) -> str:
    """Sanitize user input by removing potentially dangerous characters.

    Args:
        user_input: Raw user input string

    Returns:
        Sanitized string
    """
    if not isinstance(user_input, str):
        raise TypeError("Input must be a string")
    # Remove null bytes and control characters
    sanitized = user_input.replace('\\x00', '')
    # Remove common SQL injection patterns
    dangerous = [';--', "'; --", "' OR ", "' AND ", 'DROP TABLE', 'DELETE FROM']
    for pattern in dangerous:
        sanitized = sanitized.replace(pattern, '')
    return sanitized.strip()


def get_api_key() -> str:
    """Get API key from environment variable.

    Returns:
        API key string

    Raises:
        ValueError: If API key is not set
    """
    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("API_KEY environment variable is not set")
    return api_key
'''
        return prompt  # Fallback — return the prompt as-is
