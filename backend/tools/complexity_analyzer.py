"""Radon complexity analysis integration."""

import subprocess
import json
import os
from backend.models import Issue, Severity, IssueCategory
from backend.config import COMPLEXITY_THRESHOLD


class ComplexityAnalyzer:
    """Analyzes cyclomatic complexity and maintainability using Radon."""

    def __init__(self, threshold: int = COMPLEXITY_THRESHOLD):
        self.name = "radon"
        self.threshold = threshold

    def analyze_file(self, file_path: str) -> list[Issue]:
        """Analyze complexity of a single file."""
        issues = []
        issues.extend(self._check_cyclomatic(file_path))
        return issues

    def analyze_directory(self, dir_path: str) -> list[Issue]:
        """Analyze all Python files in a directory."""
        all_issues = []
        for root, _, files in os.walk(dir_path):
            if any(part.startswith('.') or part == '__pycache__' for part in root.split(os.sep)):
                continue
            for fname in files:
                if fname.endswith(".py"):
                    all_issues.extend(self.analyze_file(os.path.join(root, fname)))
        return all_issues

    def _check_cyclomatic(self, file_path: str) -> list[Issue]:
        """Run radon cc (cyclomatic complexity) analysis."""
        issues = []
        try:
            result = subprocess.run(
                ["python", "-m", "radon", "cc", "-j", "-n", "C", file_path],
                capture_output=True, text=True, timeout=30
            )

            if result.stdout.strip():
                data = json.loads(result.stdout)
                for fpath, blocks in data.items():
                    for block in blocks:
                        complexity = block.get("complexity", 0)
                        if complexity >= self.threshold:
                            rank = block.get("rank", "?")
                            name = block.get("name", "unknown")
                            block_type = block.get("type", "function")
                            lineno = block.get("lineno", 0)

                            if complexity >= 20:
                                sev = Severity.HIGH
                            elif complexity >= 15:
                                sev = Severity.MEDIUM
                            else:
                                sev = Severity.LOW

                            issues.append(Issue(
                                file_path=file_path,
                                line_number=lineno,
                                severity=sev,
                                category=IssueCategory.COMPLEXITY,
                                title=f"High complexity ({rank}: {complexity}) in {block_type} '{name}'",
                                description=(
                                    f"The {block_type} '{name}' has a cyclomatic complexity of {complexity} "
                                    f"(rank {rank}). Consider refactoring to reduce complexity."
                                ),
                                suggested_fix="Break the function into smaller, focused functions. Extract conditions into named boolean variables.",
                                source=self.name
                            ))

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass  # Silently skip — this is a supplementary check

        return issues

    def get_maintainability_index(self, file_path: str) -> dict:
        """Get maintainability index for a file."""
        try:
            result = subprocess.run(
                ["python", "-m", "radon", "mi", "-j", file_path],
                capture_output=True, text=True, timeout=30
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                return data
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass
        return {}
