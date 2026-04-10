"""Pydantic data models for the Code Review Agent Pipeline."""

from __future__ import annotations
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


# ── Enums ──────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    COMPLEXITY = "complexity"
    BEST_PRACTICE = "best_practice"


class AgentType(str, Enum):
    ANALYZER = "analyzer"
    PLANNER = "planner"
    FIXER = "fixer"
    VERIFIER = "verifier"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    FIXING = "fixing"
    VERIFYING = "verifying"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Core Models ────────────────────────────────────────

class Issue(BaseModel):
    """A single code issue found by the Analyzer."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    file_path: str
    line_number: int
    end_line: Optional[int] = None
    severity: Severity
    category: IssueCategory
    title: str
    description: str
    code_snippet: str = ""
    suggested_fix: str = ""
    source: str = "analyzer"  # which tool found it


class FixAction(BaseModel):
    """A single planned fix action."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    issue_id: str
    file_path: str
    approach: str
    risk_level: Severity = Severity.LOW
    priority: int = 0  # lower = higher priority
    estimated_impact: str = ""


class FixPlan(BaseModel):
    """The complete fix plan produced by the Planner."""
    actions: list[FixAction] = []
    total_issues: int = 0
    fixable_issues: int = 0
    skipped_reasons: dict[str, str] = {}  # issue_id -> reason
    summary: str = ""


class CodeChange(BaseModel):
    """A single code change made by the Fixer."""
    file_path: str
    original_code: str
    fixed_code: str
    diff: str = ""
    issue_id: str = ""
    description: str = ""
    success: bool = True


class FixResult(BaseModel):
    """Results from the Fixer agent."""
    changes: list[CodeChange] = []
    total_attempted: int = 0
    total_succeeded: int = 0
    total_failed: int = 0
    summary: str = ""


class TestResult(BaseModel):
    """A single test result."""
    test_name: str
    passed: bool
    error_message: str = ""
    duration: float = 0.0


class VerificationResult(BaseModel):
    """Results from the Verifier agent."""
    passed: bool = False
    test_results: list[TestResult] = []
    tests_passed: int = 0
    tests_failed: int = 0
    tests_total: int = 0
    syntax_valid: bool = True
    new_issues_found: int = 0
    feedback: str = ""
    details: str = ""


# ── Agent Events (for WebSocket) ───────────────────────

class AgentEvent(BaseModel):
    """Real-time event emitted by agents for the dashboard."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent: AgentType
    event_type: str  # "started", "thinking", "tool_use", "result", "error"
    title: str
    detail: str = ""
    data: dict = {}


# ── Pipeline Result ────────────────────────────────────

class PipelineResult(BaseModel):
    """Final result of the complete pipeline run."""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: PipelineStatus = PipelineStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    target_path: str = ""

    # Agent results
    issues: list[Issue] = []
    fix_plan: Optional[FixPlan] = None
    fix_result: Optional[FixResult] = None
    verification: Optional[VerificationResult] = None

    # Execution trace
    events: list[AgentEvent] = []
    retry_count: int = 0
    total_duration: float = 0.0

    # Summary
    summary: str = ""
    error: str = ""


class ReviewRequest(BaseModel):
    """Incoming review request from the API."""
    target_path: str = ""
    repo_url: str = ""
    demo: bool = False
