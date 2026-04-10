"""Multi-Agent Orchestrator — controls the full pipeline with retry logic."""

from __future__ import annotations
import asyncio
import logging
import os
import shutil
from datetime import datetime
from typing import Any, Callable, Optional

from backend.config import MAX_RETRIES, TEMP_DIR
from backend.models import (
    AgentEvent, PipelineResult, PipelineStatus
)
from backend.agents.analyzer_agent import AnalyzerAgent
from backend.agents.planner_agent import PlannerAgent
from backend.agents.fixer_agent import FixerAgent
from backend.agents.verifier_agent import VerifierAgent
from backend.tools.git_tools import GitTools

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Controls the full agent pipeline:
        Analyze → Plan → Fix → Verify (→ Retry if failed)

    Features:
    - Sequential agent execution with shared context
    - Retry loop with verification feedback
    - Real-time event streaming via callback
    - Full execution trace for reports
    """

    def __init__(self, event_callback: Optional[Callable] = None):
        self.event_callback = event_callback
        self.git_tools = GitTools()
        self.max_retries = MAX_RETRIES

    async def _emit(self, event: AgentEvent):
        """Forward agent events to the registered callback."""
        if self.event_callback:
            try:
                await self.event_callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    async def run(self, target_path: str = "", repo_url: str = "",
                  demo: bool = False) -> PipelineResult:
        """
        Run the full code review pipeline.

        Args:
            target_path: Local path to analyze
            repo_url: Git repo URL to clone and analyze
            demo: If True, use sample project
        """
        result = PipelineResult(
            started_at=datetime.utcnow(),
            target_path=target_path
        )

        workspace = None
        try:
            # ── Resolve target ──
            if demo:
                from backend.config import SAMPLE_PROJECTS_DIR
                target_path = str(SAMPLE_PROJECTS_DIR / "buggy_calculator")
                result.target_path = target_path

            if repo_url:
                result.status = PipelineStatus.ANALYZING
                workspace = os.path.join(str(TEMP_DIR), f"ws_{result.job_id[:8]}")
                target_path = self.git_tools.clone_repo(repo_url, workspace)
                result.target_path = target_path

            if not target_path or not os.path.exists(target_path):
                result.status = PipelineStatus.FAILED
                result.error = f"Target path does not exist: {target_path}"
                return result

            # Create a working copy for modifications
            workspace_dir = os.path.join(str(TEMP_DIR), f"ws_{result.job_id[:8]}")
            if not workspace:
                workspace = self.git_tools.create_workspace(target_path, workspace_dir)
            working_path = workspace

            # Shared context passed between agents
            context: dict[str, Any] = {
                "target_path": working_path,
                "original_path": target_path,
            }

            # ── Stage 1: ANALYZE ──
            result.status = PipelineStatus.ANALYZING
            analyzer = AnalyzerAgent(event_callback=self._emit)
            analysis = await analyzer.execute(context)
            context["issues"] = analysis.get("issues", [])
            result.issues = [
                __import__('backend.models', fromlist=['Issue']).Issue(**i)
                if isinstance(i, dict) else i
                for i in context["issues"]
            ]

            if not context["issues"]:
                result.status = PipelineStatus.COMPLETED
                result.summary = "No issues found — code looks clean! 🎉"
                result.completed_at = datetime.utcnow()
                return result

            # ── Stage 2: PLAN ──
            result.status = PipelineStatus.PLANNING
            planner = PlannerAgent(event_callback=self._emit)
            plan_result = await planner.execute(context)
            context["fix_plan"] = plan_result.get("fix_plan", {})
            result.fix_plan = __import__('backend.models', fromlist=['FixPlan']).FixPlan(
                **context["fix_plan"]
            ) if isinstance(context["fix_plan"], dict) else context["fix_plan"]

            # ── Stage 3 & 4: FIX → VERIFY (with retry loop) ──
            for attempt in range(self.max_retries):
                # Fix
                result.status = PipelineStatus.FIXING
                if attempt > 0:
                    result.status = PipelineStatus.RETRYING
                    result.retry_count = attempt

                fixer = FixerAgent(event_callback=self._emit)
                fix_result = await fixer.execute(context)
                context["fix_result"] = fix_result.get("fix_result", {})
                result.fix_result = __import__('backend.models', fromlist=['FixResult']).FixResult(
                    **context["fix_result"]
                ) if isinstance(context["fix_result"], dict) else context["fix_result"]

                # Verify
                result.status = PipelineStatus.VERIFYING
                verifier = VerifierAgent(event_callback=self._emit)
                verify_result = await verifier.execute(context)
                verification = verify_result.get("verification", {})
                result.verification = __import__('backend.models', fromlist=['VerificationResult']).VerificationResult(
                    **verification
                ) if isinstance(verification, dict) else verification

                if result.verification.passed:
                    break

                # Prepare feedback for retry
                context["verification_feedback"] = result.verification.feedback
                logger.info(f"Attempt {attempt + 1} failed, retrying...")

            # ── Finalize ──
            result.status = PipelineStatus.COMPLETED
            result.completed_at = datetime.utcnow()
            result.total_duration = (
                result.completed_at - result.started_at
            ).total_seconds()

            # Copy fixed files back to show diffs
            result.summary = self._build_final_summary(result)

        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.utcnow()

        return result

    def _build_final_summary(self, result: PipelineResult) -> str:
        """Build a human-readable summary of the pipeline execution."""
        parts = [
            f"Code Review Pipeline — {'✅ PASSED' if result.verification and result.verification.passed else '⚠️ COMPLETED WITH ISSUES'}",
            f"",
            f"📊 Analysis: {len(result.issues)} issues found",
        ]

        if result.fix_plan:
            parts.append(f"📋 Plan: {result.fix_plan.fixable_issues} fixable issues")

        if result.fix_result:
            parts.append(
                f"🔧 Fixes: {result.fix_result.total_succeeded} succeeded, "
                f"{result.fix_result.total_failed} failed"
            )

        if result.verification:
            parts.append(
                f"✅ Tests: {result.verification.tests_passed}/{result.verification.tests_total} passed"
            )

        if result.retry_count > 0:
            parts.append(f"🔄 Retries: {result.retry_count}")

        parts.append(f"⏱️ Duration: {result.total_duration:.1f}s")

        return "\n".join(parts)
