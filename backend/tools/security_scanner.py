"""Bandit security scanner integration."""

import subprocess
import json
import os
from backend.models import Issue, Severity, IssueCategory


BANDIT_SEVERITY_MAP = {
    "HIGH": Severity.CRITICAL,
    "MEDIUM": Severity.HIGH,
    "LOW": Severity.MEDIUM,
}


class SecurityScanner:
    """Runs Bandit security analysis on Python code."""

    def __init__(self):
        self.name = "bandit"

    def analyze_file(self, file_path: str) -> list[Issue]:
        """Run bandit on a single file."""
        return self._run_bandit(file_path)

    def analyze_directory(self, dir_path: str) -> list[Issue]:
        """Run bandit on all Python files in a directory."""
        return self._run_bandit(dir_path, recursive=True)

    def _run_bandit(self, target: str, recursive: bool = False) -> list[Issue]:
        """Execute bandit and parse JSON output."""
        issues = []
        cmd = ["python", "-m", "bandit", "-f", "json", "-ll"]

        if recursive:
            cmd.extend(["-r", target])
        else:
            cmd.append(target)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )

            output = result.stdout.strip()
            if output:
                data = json.loads(output)
                for finding in data.get("results", []):
                    sev = finding.get("issue_severity", "LOW")
                    issues.append(Issue(
                        file_path=finding.get("filename", ""),
                        line_number=finding.get("line_number", 0),
                        end_line=finding.get("end_col_offset"),
                        severity=BANDIT_SEVERITY_MAP.get(sev, Severity.MEDIUM),
                        category=IssueCategory.SECURITY,
                        title=f"[{finding.get('test_id', '')}] {finding.get('test_name', '')}",
                        description=finding.get("issue_text", ""),
                        code_snippet=finding.get("code", ""),
                        suggested_fix=f"Confidence: {finding.get('issue_confidence', 'N/A')}. "
                                      f"See: {finding.get('more_info', 'N/A')}",
                        source=self.name
                    ))

        except subprocess.TimeoutExpired:
            issues.append(Issue(
                file_path=target, line_number=0, severity=Severity.INFO,
                category=IssueCategory.SECURITY, title="Bandit timeout",
                description="Security scan timed out after 60 seconds.",
                source=self.name
            ))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            issues.append(Issue(
                file_path=target, line_number=0, severity=Severity.INFO,
                category=IssueCategory.SECURITY, title="Bandit execution error",
                description=f"Could not run bandit: {e}",
                source=self.name
            ))

        return issues
