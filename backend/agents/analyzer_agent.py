"""Analyzer Agent — scans codebases for bugs, security issues, and code smells."""

from __future__ import annotations
import os
import json
from typing import Any, Optional, Callable

from backend.agents.base_agent import BaseAgent
from backend.models import AgentType, Issue, Severity, IssueCategory
from backend.tools.code_parser import CodeParser
from backend.tools.linter import LinterTool
from backend.tools.security_scanner import SecurityScanner
from backend.tools.complexity_analyzer import ComplexityAnalyzer


class AnalyzerAgent(BaseAgent):
    """
    Agent 1: Analyzes Python codebases using multiple tools.

    Tools: AST Parser, Pylint, Bandit, Radon
    Output: List of Issues with severity, category, and suggested fixes
    """

    def __init__(self, event_callback: Optional[Callable] = None):
        super().__init__(event_callback)
        self.parser = CodeParser()
        self.linter = LinterTool()
        self.scanner = SecurityScanner()
        self.complexity = ComplexityAnalyzer()

    @property
    def agent_type(self) -> AgentType:
        return AgentType.ANALYZER

    @property
    def name(self) -> str:
        return "Analyzer Agent"

    @property
    def system_prompt(self) -> str:
        return (
            "You are an expert code analyzer. You review code analysis results from "
            "multiple tools (AST parser, Pylint, Bandit, Radon) and synthesize them "
            "into a prioritized, deduplicated list of issues. You identify the most "
            "critical problems first and provide actionable descriptions."
        )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze the target project using all available tools.

        Context keys:
            - target_path: str — path to the project to analyze
        """
        target_path = context.get("target_path", "")
        if not target_path or not os.path.exists(target_path):
            return {"issues": [], "error": f"Invalid target path: {target_path}"}

        await self.emit_event("started", "Starting code analysis",
                              f"Scanning {target_path}")

        import asyncio

        all_issues: list[Issue] = []

        # ── Step 1: AST Parsing ──
        await self.emit_event("tool_use", "Running AST Parser",
                              "Detecting structural issues, unused imports, dangerous patterns")
        try:
            ast_issues = await asyncio.to_thread(self.parser.analyze_directory, target_path)
            all_issues.extend(ast_issues)
            await self.emit_event("result", f"AST Parser found {len(ast_issues)} issues",
                                  self._summarize_issues(ast_issues))
        except Exception as e:
            await self.emit_event("error", "AST Parser failed", str(e))

        # ── Step 2: Pylint ──
        await self.emit_event("tool_use", "Running Pylint",
                              "Checking code style, errors, and conventions")
        try:
            lint_issues = await asyncio.to_thread(self.linter.analyze_directory, target_path)
            all_issues.extend(lint_issues)
            await self.emit_event("result", f"Pylint found {len(lint_issues)} issues",
                                  self._summarize_issues(lint_issues))
        except Exception as e:
            await self.emit_event("error", "Pylint failed", str(e))

        # ── Step 3: Bandit Security Scan ──
        await self.emit_event("tool_use", "Running Security Scanner (Bandit)",
                              "Scanning for security vulnerabilities")
        try:
            sec_issues = await asyncio.to_thread(self.scanner.analyze_directory, target_path)
            all_issues.extend(sec_issues)
            await self.emit_event("result", f"Bandit found {len(sec_issues)} security issues",
                                  self._summarize_issues(sec_issues))
        except Exception as e:
            await self.emit_event("error", "Bandit failed", str(e))

        # ── Step 4: Complexity Analysis ──
        await self.emit_event("tool_use", "Running Complexity Analyzer (Radon)",
                              "Measuring cyclomatic complexity")
        try:
            cx_issues = await asyncio.to_thread(self.complexity.analyze_directory, target_path)
            all_issues.extend(cx_issues)
            await self.emit_event("result", f"Radon found {len(cx_issues)} complexity issues",
                                  self._summarize_issues(cx_issues))
        except Exception as e:
            await self.emit_event("error", "Radon failed", str(e))

        # ── Step 5: LLM-powered deduplication and enrichment ──
        await self.emit_event("thinking", "AI analyzing and prioritizing issues",
                              f"Processing {len(all_issues)} total findings")

        deduplicated = self._deduplicate_issues(all_issues)

        # Use LLM to enrich descriptions if available
        if len(deduplicated) > 0:
            enrichment_prompt = self._build_enrichment_prompt(deduplicated)
            llm_response = await self._call_llm(enrichment_prompt)
            deduplicated = self._apply_enrichment(deduplicated, llm_response)

        await self.emit_event("result",
                              f"Analysis complete: {len(deduplicated)} unique issues found",
                              self._build_summary(deduplicated))

        return {
            "issues": [issue.model_dump() for issue in deduplicated],
            "total_files_scanned": self._count_py_files(target_path),
            "summary": self._build_summary(deduplicated)
        }

    def _deduplicate_issues(self, issues: list[Issue]) -> list[Issue]:
        """Remove duplicate issues (same file, line, similar title)."""
        seen = set()
        unique = []
        for issue in issues:
            key = (issue.file_path, issue.line_number, issue.category)
            if key not in seen:
                seen.add(key)
                unique.append(issue)

        # Sort by severity (critical first)
        severity_order = {
            Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2,
            Severity.LOW: 3, Severity.INFO: 4
        }
        unique.sort(key=lambda i: severity_order.get(i.severity, 5))
        return unique

    def _build_enrichment_prompt(self, issues: list[Issue]) -> str:
        """Build a prompt for the LLM to enrich issue descriptions."""
        issues_text = "\n".join([
            f"- [{i.severity.value}] {i.file_path}:{i.line_number} — {i.title}: {i.description}"
            for i in issues[:20]  # Limit to avoid token overflow
        ])
        return f"""Here are code issues found by automated tools. For each, provide a brief 
improved description and a concrete fix suggestion. Return as JSON array with 
keys: "index" (0-based), "description", "suggested_fix".

Issues:
{issues_text}

Return ONLY valid JSON array, no extra text."""

    def _apply_enrichment(self, issues: list[Issue], llm_response: str) -> list[Issue]:
        """Apply LLM enrichment to issue descriptions."""
        try:
            # Try to find JSON in the response
            response = llm_response.strip()
            if "```" in response:
                response = response.split("```")[1].strip()
                if response.startswith("json"):
                    response = response[4:].strip()
            enrichments = json.loads(response)
            for item in enrichments:
                idx = item.get("index", -1)
                if 0 <= idx < len(issues):
                    if item.get("description"):
                        issues[idx].description = item["description"]
                    if item.get("suggested_fix"):
                        issues[idx].suggested_fix = item["suggested_fix"]
        except (json.JSONDecodeError, KeyError, IndexError):
            pass  # Keep original descriptions if enrichment fails
        return issues

    def _summarize_issues(self, issues: list[Issue]) -> str:
        """Create a brief summary of issues by severity."""
        counts = {}
        for issue in issues:
            counts[issue.severity.value] = counts.get(issue.severity.value, 0) + 1
        return ", ".join(f"{v} {k}" for k, v in counts.items())

    def _build_summary(self, issues: list[Issue]) -> str:
        """Build a comprehensive summary for the final report."""
        by_category = {}
        by_severity = {}
        for issue in issues:
            by_category.setdefault(issue.category.value, []).append(issue)
            by_severity.setdefault(issue.severity.value, []).append(issue)

        parts = [f"Found {len(issues)} issues across {len(set(i.file_path for i in issues))} files:"]
        for sev in ["critical", "high", "medium", "low", "info"]:
            if sev in by_severity:
                parts.append(f"  • {sev.upper()}: {len(by_severity[sev])}")
        return "\n".join(parts)

    def _count_py_files(self, path: str) -> int:
        """Count Python files in directory."""
        count = 0
        for root, _, files in os.walk(path):
            if '__pycache__' in root:
                continue
            count += sum(1 for f in files if f.endswith('.py'))
        return count

    def _get_demo_response(self, prompt: str) -> str:
        """Demo mode enrichment response."""
        return json.dumps([
            {"index": 0, "description": "Using eval() on untrusted input allows arbitrary code execution — an attacker can run os.system('rm -rf /') via this endpoint.",
             "suggested_fix": "Replace eval() with ast.literal_eval() for safe evaluation of literal expressions."},
            {"index": 1, "description": "exec() executes arbitrary Python code from a string, enabling full remote code execution if the input is user-controlled.",
             "suggested_fix": "Remove exec() entirely and use a safe config parser like json.load() or configparser."},
            {"index": 2, "description": "Using eval() here allows arbitrary code injection — any user input is executed as Python code.",
             "suggested_fix": "Replace with ast.literal_eval() or a proper expression parser."},
            {"index": 3, "description": "Mutable default argument [] is shared across all function calls, causing results to accumulate between invocations.",
             "suggested_fix": "Use None as default: def batch_calculate(operations, results=None): if results is None: results = []"},
            {"index": 4, "description": "Bare 'except:' catches SystemExit and KeyboardInterrupt, making the program impossible to kill cleanly.",
             "suggested_fix": "Replace 'except:' with 'except Exception as e:' to only catch standard errors."},
            {"index": 5, "description": "No zero-division guard — calling divide(10, 0) will crash with an unhandled ZeroDivisionError.",
             "suggested_fix": "Add: if b == 0: raise ValueError('Cannot divide by zero')"},
            {"index": 6, "description": "os.system() passes the command string directly to the shell, enabling command injection attacks.",
             "suggested_fix": "Use subprocess.run() with a list of arguments and shell=False."},
            {"index": 7, "description": "pickle.loads() on untrusted data can execute arbitrary code during deserialization.",
             "suggested_fix": "Use json.loads() or a safe serialization format instead of pickle for untrusted data."},
        ])
