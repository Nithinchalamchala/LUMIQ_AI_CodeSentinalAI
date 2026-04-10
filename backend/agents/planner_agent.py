"""Planner Agent — creates prioritized fix plans from analysis results."""

from __future__ import annotations
import json
from typing import Any, Optional, Callable

from backend.agents.base_agent import BaseAgent
from backend.models import (
    AgentType, Issue, Severity, IssueCategory,
    FixAction, FixPlan
)


class PlannerAgent(BaseAgent):
    """
    Agent 2: Creates a prioritized fix plan from analyzed issues.

    Uses LLM reasoning to:
    - Prioritize fixes by severity and dependencies
    - Determine which issues are auto-fixable
    - Plan the order of changes to minimize conflicts
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.PLANNER

    @property
    def name(self) -> str:
        return "Planner Agent"

    @property
    def system_prompt(self) -> str:
        return (
            "You are an expert software engineering planner. Given a list of code issues, "
            "you create a prioritized fix plan. You consider: fix severity (critical first), "
            "dependencies between fixes (foundational fixes first), risk level, and "
            "whether each fix can be automated safely. Return structured JSON plans."
        )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Create a fix plan from analyzed issues.

        Context keys:
            - issues: list[dict] — issues from the Analyzer
            - target_path: str — path to the project
        """
        raw_issues = context.get("issues", [])
        issues = [Issue(**i) if isinstance(i, dict) else i for i in raw_issues]

        if not issues:
            return {"fix_plan": FixPlan(summary="No issues to fix.").model_dump()}

        await self.emit_event("started", "Planning fixes",
                              f"Analyzing {len(issues)} issues to create fix plan")

        # ── Step 1: Classify fixability ──
        await self.emit_event("thinking", "Classifying issues by fixability",
                              "Determining which issues can be auto-fixed safely")

        fixable = []
        skipped = {}

        for issue in issues:
            if issue.severity == Severity.INFO:
                skipped[issue.id] = "Info-level issues are not actionable"
                continue
            if issue.category == IssueCategory.STYLE and issue.severity == Severity.LOW:
                skipped[issue.id] = "Minor style issues skipped for auto-fix"
                continue
            fixable.append(issue)

        await self.emit_event("result",
                              f"{len(fixable)} issues are fixable, {len(skipped)} skipped",
                              f"Fixable: {len(fixable)}, Skipped: {len(skipped)}")

        # ── Step 2: Use LLM to prioritize and plan ──
        await self.emit_event("thinking", "AI creating fix strategy",
                              "Determining optimal fix order and approaches")

        plan_prompt = self._build_plan_prompt(fixable)
        llm_response = await self._call_llm(plan_prompt)

        # ── Step 3: Parse LLM response into FixPlan ──
        actions = self._parse_plan_response(llm_response, fixable)

        fix_plan = FixPlan(
            actions=actions,
            total_issues=len(issues),
            fixable_issues=len(fixable),
            skipped_reasons=skipped,
            summary=f"Fix plan with {len(actions)} actions for {len(fixable)} issues. "
                    f"{len(skipped)} issues skipped."
        )

        await self.emit_event("result", f"Fix plan created with {len(actions)} actions",
                              fix_plan.summary)

        return {"fix_plan": fix_plan.model_dump()}

    def _build_plan_prompt(self, issues: list[Issue]) -> str:
        """Build a prompt for the LLM to create a fix plan."""
        issues_json = []
        for i, issue in enumerate(issues[:15]):  # Limit to top 15
            issues_json.append({
                "index": i,
                "id": issue.id,
                "file": issue.file_path,
                "line": issue.line_number,
                "severity": issue.severity.value,
                "category": issue.category.value,
                "title": issue.title,
                "description": issue.description,
                "suggested_fix": issue.suggested_fix
            })

        return f"""You are planning code fixes. For each issue, create a fix action.

Issues to fix:
{json.dumps(issues_json, indent=2)}

Return a JSON array of fix actions, ordered by priority (most critical first). Each action:
{{
    "issue_index": <int>,
    "approach": "<specific fix approach>",
    "risk_level": "low|medium|high",
    "priority": <int, 0=highest>,
    "estimated_impact": "<what this fix improves>"
}}

Return ONLY valid JSON array. No extra text."""

    def _parse_plan_response(self, response: str, issues: list[Issue]) -> list[FixAction]:
        """Parse the LLM response into FixAction objects."""
        actions = []
        try:
            text = response.strip()
            if "```" in text:
                text = text.split("```")[1].strip()
                if text.startswith("json"):
                    text = text[4:].strip()
            plan_data = json.loads(text)

            for item in plan_data:
                idx = item.get("issue_index", -1)
                if 0 <= idx < len(issues):
                    issue = issues[idx]
                    risk_map = {"low": Severity.LOW, "medium": Severity.MEDIUM, "high": Severity.HIGH}
                    actions.append(FixAction(
                        issue_id=issue.id,
                        file_path=issue.file_path,
                        approach=item.get("approach", issue.suggested_fix or "Apply suggested fix"),
                        risk_level=risk_map.get(item.get("risk_level", "low"), Severity.LOW),
                        priority=item.get("priority", idx),
                        estimated_impact=item.get("estimated_impact", "")
                    ))
        except (json.JSONDecodeError, KeyError, IndexError):
            # Fallback: create actions from issues directly
            for i, issue in enumerate(issues):
                actions.append(FixAction(
                    issue_id=issue.id,
                    file_path=issue.file_path,
                    approach=issue.suggested_fix or "Apply standard fix for this issue type",
                    priority=i,
                    estimated_impact=f"Fixes {issue.severity.value} {issue.category.value} issue"
                ))

        actions.sort(key=lambda a: a.priority)
        return actions

    def _get_demo_response(self, prompt: str) -> str:
        """Demo mode plan response."""
        return json.dumps([
            {"issue_index": 0, "approach": "Add zero-division check with proper error handling using ValueError",
             "risk_level": "low", "priority": 0, "estimated_impact": "Prevents runtime crashes on division by zero"},
            {"issue_index": 1, "approach": "Replace eval() with ast.literal_eval() for safe expression evaluation",
             "risk_level": "low", "priority": 1, "estimated_impact": "Eliminates critical security vulnerability"},
            {"issue_index": 2, "approach": "Replace mutable default [] with None and initialize inside function body",
             "risk_level": "low", "priority": 2, "estimated_impact": "Fixes subtle bug where list is shared across calls"},
            {"issue_index": 3, "approach": "Replace bare except with 'except Exception:' to avoid catching SystemExit",
             "risk_level": "low", "priority": 3, "estimated_impact": "Improves error handling predictability"},
            {"issue_index": 4, "approach": "Remove unused import statement to clean up module namespace",
             "risk_level": "low", "priority": 4, "estimated_impact": "Improves code readability and maintenance"},
        ])
