"""Pylint integration for code style and error detection."""

import subprocess
import json
import os
from backend.models import Issue, Severity, IssueCategory


# Map pylint message types to our severity levels
PYLINT_SEVERITY_MAP = {
    "fatal": Severity.CRITICAL,
    "error": Severity.HIGH,
    "warning": Severity.MEDIUM,
    "convention": Severity.LOW,
    "refactor": Severity.LOW,
    "information": Severity.INFO,
}

# Map pylint message IDs to categories
PYLINT_CATEGORY_MAP = {
    "C": IssueCategory.STYLE,       # Convention
    "R": IssueCategory.COMPLEXITY,   # Refactor
    "W": IssueCategory.BEST_PRACTICE,  # Warning
    "E": IssueCategory.BUG,         # Error
    "F": IssueCategory.BUG,         # Fatal
}


class LinterTool:
    """Runs Pylint on Python files and returns structured issues."""

    def __init__(self):
        self.name = "pylint"

    def analyze_file(self, file_path: str) -> list[Issue]:
        """Run pylint on a single file and return issues."""
        return self._run_pylint([file_path])

    def analyze_directory(self, dir_path: str) -> list[Issue]:
        """Run pylint on all Python files in a directory."""
        py_files = []
        for root, _, files in os.walk(dir_path):
            if any(part.startswith('.') or part == '__pycache__' for part in root.split(os.sep)):
                continue
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))

        if not py_files:
            return []
        return self._run_pylint(py_files)

    def _run_pylint(self, files: list[str]) -> list[Issue]:
        """Execute pylint and parse the JSON output."""
        issues = []
        try:
            result = subprocess.run(
                [
                    "python", "-m", "pylint",
                    "--output-format=json",
                    "--disable=C0114,C0115,C0116",  # Skip missing docstrings
                    "--max-line-length=120",
                    *files
                ],
                capture_output=True, text=True, timeout=60
            )

            if result.stdout.strip():
                messages = json.loads(result.stdout)
                for msg in messages:
                    msg_type = msg.get("type", "convention")
                    msg_id = msg.get("message-id", "C0000")
                    category_key = msg_id[0] if msg_id else "C"

                    issues.append(Issue(
                        file_path=msg.get("path", ""),
                        line_number=msg.get("line", 0),
                        end_line=msg.get("endLine"),
                        severity=PYLINT_SEVERITY_MAP.get(msg_type, Severity.LOW),
                        category=PYLINT_CATEGORY_MAP.get(category_key, IssueCategory.STYLE),
                        title=f"[{msg_id}] {msg.get('symbol', 'unknown')}",
                        description=msg.get("message", ""),
                        code_snippet=f"Line {msg.get('line', '?')}, Column {msg.get('column', '?')}",
                        source=self.name
                    ))

        except subprocess.TimeoutExpired:
            issues.append(Issue(
                file_path=files[0] if files else "unknown",
                line_number=0, severity=Severity.INFO,
                category=IssueCategory.STYLE,
                title="Pylint timeout",
                description="Pylint analysis timed out after 60 seconds.",
                source=self.name
            ))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            issues.append(Issue(
                file_path=files[0] if files else "unknown",
                line_number=0, severity=Severity.INFO,
                category=IssueCategory.STYLE,
                title="Pylint execution error",
                description=f"Could not run pylint: {e}",
                source=self.name
            ))

        return issues
