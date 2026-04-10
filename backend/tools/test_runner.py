"""Test runner tool using pytest."""

import subprocess
import os
from backend.models import TestResult


class TestRunner:
    """Executes test suites and returns structured results."""

    def __init__(self):
        self.name = "pytest"

    def run_tests(self, project_path: str) -> list[TestResult]:
        """Run pytest on a project and return structured test results."""
        results = []

        # Find test files
        test_files = self._find_test_files(project_path)
        if not test_files:
            return [TestResult(
                test_name="no_tests_found",
                passed=True,
                error_message="No test files found in the project."
            )]

        try:
            result = subprocess.run(
                [
                    "python", "-m", "pytest",
                    project_path,
                    "-v",
                    "--tb=short",
                    "--no-header",
                    "-q"
                ],
                capture_output=True, text=True, timeout=120,
                cwd=project_path
            )

            output = result.stdout + result.stderr
            results = self._parse_pytest_output(output)

            # If no results were parsed but pytest ran, create a summary result
            if not results:
                passed = result.returncode == 0
                results.append(TestResult(
                    test_name="test_suite",
                    passed=passed,
                    error_message="" if passed else output[-500:] if len(output) > 500 else output
                ))

        except subprocess.TimeoutExpired:
            results.append(TestResult(
                test_name="timeout",
                passed=False,
                error_message="Test execution timed out after 120 seconds."
            ))
        except FileNotFoundError:
            results.append(TestResult(
                test_name="missing_pytest",
                passed=False,
                error_message="pytest is not installed."
            ))

        return results

    def _find_test_files(self, project_path: str) -> list[str]:
        """Find all test files in a project."""
        test_files = []
        for root, _, files in os.walk(project_path):
            if '__pycache__' in root:
                continue
            for f in files:
                if f.startswith("test_") and f.endswith(".py"):
                    test_files.append(os.path.join(root, f))
                elif f.endswith("_test.py"):
                    test_files.append(os.path.join(root, f))
        return test_files

    def _parse_pytest_output(self, output: str) -> list[TestResult]:
        """Parse pytest verbose output into TestResult objects."""
        results = []
        for line in output.splitlines():
            line = line.strip()
            if " PASSED" in line:
                test_name = line.split(" PASSED")[0].strip()
                results.append(TestResult(test_name=test_name, passed=True))
            elif " FAILED" in line:
                test_name = line.split(" FAILED")[0].strip()
                # Try to capture the error from subsequent lines
                results.append(TestResult(
                    test_name=test_name, passed=False,
                    error_message=f"Test failed. See full output for details."
                ))
            elif " ERROR" in line:
                test_name = line.split(" ERROR")[0].strip()
                results.append(TestResult(
                    test_name=test_name, passed=False,
                    error_message="Error during test collection or execution."
                ))
        return results

    def check_syntax(self, file_path: str) -> tuple[bool, str]:
        """Check if a Python file has valid syntax."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            compile(source, file_path, "exec")
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)
