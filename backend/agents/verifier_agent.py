"""Verifier Agent — validates fixes by running tests and re-checking code."""

from __future__ import annotations
import os
import json
from typing import Any, Optional, Callable

from backend.agents.base_agent import BaseAgent
from backend.models import (
    AgentType, FixResult, VerificationResult, TestResult
)
from backend.tools.test_runner import TestRunner
from backend.tools.code_parser import CodeParser


class VerifierAgent(BaseAgent):
    """
    Agent 4: Verifies that fixes are correct.

    Steps:
    1. Check syntax of all modified files
    2. Run the project's test suite
    3. Re-scan for new issues introduced by fixes
    4. Provide pass/fail verdict with detailed feedback
    """

    def __init__(self, event_callback: Optional[Callable] = None):
        super().__init__(event_callback)
        self.test_runner = TestRunner()
        self.code_parser = CodeParser()

    @property
    def agent_type(self) -> AgentType:
        return AgentType.VERIFIER

    @property
    def name(self) -> str:
        return "Verifier Agent"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a quality assurance expert. You review code changes and test results "
            "to determine if fixes are correct and complete. You provide detailed feedback "
            "about any remaining issues."
        )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Verify the fixes applied by the Fixer.

        Context keys:
            - fix_result: dict — results from the Fixer
            - target_path: str — project path
        """
        fix_data = context.get("fix_result", {})
        fix_result = FixResult(**fix_data) if isinstance(fix_data, dict) else fix_data
        target_path = context.get("target_path", "")

        await self.emit_event("started", "Verifying fixes",
                              f"Checking {len(fix_result.changes)} modified files")

        verification = VerificationResult()
        issues_found = []

        # ── Step 1: Syntax Check ──
        await self.emit_event("tool_use", "Checking syntax validity",
                              "Compiling all modified files")

        all_syntax_valid = True
        for change in fix_result.changes:
            full_path = change.file_path
            if not os.path.isabs(full_path):
                full_path = os.path.join(target_path, change.file_path)

            valid, error = self.test_runner.check_syntax(full_path)
            if not valid:
                all_syntax_valid = False
                issues_found.append(f"Syntax error in {change.file_path}: {error}")
                await self.emit_event("error",
                                      f"Syntax error in {os.path.basename(change.file_path)}",
                                      error)

        verification.syntax_valid = all_syntax_valid
        if all_syntax_valid:
            await self.emit_event("result", "All files pass syntax check", "✓ No syntax errors")

        # ── Step 2: Run Tests ──
        await self.emit_event("tool_use", "Running test suite",
                              f"Executing pytest on {target_path}")

        test_results = self.test_runner.run_tests(target_path)
        verification.test_results = test_results
        verification.tests_total = len(test_results)
        verification.tests_passed = sum(1 for t in test_results if t.passed)
        verification.tests_failed = sum(1 for t in test_results if not t.passed)

        if verification.tests_failed > 0:
            failed_names = [t.test_name for t in test_results if not t.passed]
            await self.emit_event("error",
                                  f"{verification.tests_failed} tests failed",
                                  ", ".join(failed_names[:5]))
            issues_found.append(
                f"Failed tests: {', '.join(failed_names)}"
            )
        else:
            await self.emit_event("result",
                                  f"All {verification.tests_passed} tests passed", "✓ Test suite green")

        # ── Step 3: Re-scan for New Issues ──
        await self.emit_event("tool_use", "Re-scanning for new issues",
                              "Checking if fixes introduced new problems")

        new_issues = self.code_parser.analyze_directory(target_path)
        # Filter to only critical/high issues
        critical_new = [i for i in new_issues
                        if i.severity.value in ("critical", "high")]
        verification.new_issues_found = len(critical_new)

        if critical_new:
            await self.emit_event("error",
                                  f"{len(critical_new)} critical/high issues remain",
                                  "; ".join(i.title for i in critical_new[:3]))
            issues_found.extend(
                f"Remaining issue: {i.title} in {i.file_path}:{i.line_number}"
                for i in critical_new[:5]
            )

        # ── Step 4: LLM Verdict ──
        await self.emit_event("thinking", "AI evaluating overall fix quality",
                              "Synthesizing test results and re-scan findings")

        verdict_prompt = self._build_verdict_prompt(
            fix_result, verification, issues_found
        )
        verdict_response = await self._call_llm(verdict_prompt)

        # Parse verdict
        passed, feedback = self._parse_verdict(verdict_response)

        verification.passed = passed and all_syntax_valid
        verification.feedback = feedback
        verification.details = "\n".join(issues_found) if issues_found else "All checks passed."

        status = "✅ PASSED" if verification.passed else "❌ FAILED"
        await self.emit_event("result", f"Verification {status}", feedback[:200])

        return {"verification": verification.model_dump()}

    def _build_verdict_prompt(self, fix_result: FixResult,
                              verification: VerificationResult,
                              issues: list[str]) -> str:
        """Build a prompt for the LLM to evaluate the fix quality."""
        return f"""Evaluate these code fix results and determine if they pass verification.

Fix Summary:
- Files modified: {len(fix_result.changes)}
- Fixes succeeded: {fix_result.total_succeeded}
- Fixes failed: {fix_result.total_failed}

Test Results:
- Tests passed: {verification.tests_passed}/{verification.tests_total}
- Syntax valid: {verification.syntax_valid}
- New critical issues: {verification.new_issues_found}

Issues found during verification:
{chr(10).join(issues) if issues else "None"}

Return JSON: {{"passed": true/false, "feedback": "detailed feedback string"}}
Return ONLY valid JSON."""

    def _parse_verdict(self, response: str) -> tuple[bool, str]:
        """Parse the LLM verdict response."""
        try:
            text = response.strip()
            if "```" in text:
                text = text.split("```")[1].strip()
                if text.startswith("json"):
                    text = text[4:].strip()
            data = json.loads(text)
            return data.get("passed", False), data.get("feedback", "No feedback provided.")
        except (json.JSONDecodeError, KeyError):
            # Try to infer from text
            is_pass = "pass" in response.lower() and "fail" not in response.lower()
            return is_pass, response[:300]

    def _get_demo_response(self, prompt: str) -> str:
        """Demo mode verdict."""
        return json.dumps({
            "passed": True,
            "feedback": "All fixes verified successfully. Division by zero is now handled with "
                        "proper ValueError. eval() replaced with ast.literal_eval(). Mutable "
                        "defaults replaced with None pattern. All 8 tests pass. No new critical "
                        "issues introduced."
        })
