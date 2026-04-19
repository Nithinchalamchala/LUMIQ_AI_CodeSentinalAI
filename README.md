# CodeSentinel AI - Autonomous Code Review Agent

## Overview
CodeSentinel AI is a sophisticated, multi-agent code review pipeline designed to autonomously analyze, plan, fix, and verify code quality. Built upon the ReAct (Reasoning and Acting) agentic architecture, it orchestrates multiple specialized AI workflows alongside deterministic static analysis tools. This ensures high-accuracy remediation of vulnerabilities, logic errors, and anti-patterns without the hallucination risks common in standard LLM implementations.

## Key Features
- Privacy-First Execution: Entirely powered by local Large Language Models (LLaMA 3 via Ollama), ensuring zero data exfiltration or third-party API dependencies.
- Multi-Agent Orchestration: Utilizes a four-stage ReAct pipeline (Analyze, Plan, Fix, Verify) to simulate a Senior DevOps Engineer's review process.
- Deterministic Tooling Integration: Combines LLM heuristics with concrete AST parsing, Pylint, Bandit, and Radon metrics.
- Asynchronous Event Streaming: Leverages FastAPI WebSockets to stream agent thought processes and state changes in real-time to the frontend.
- Glassmorphism UI: A clean, lightweight, and modern dashboard with syntax-highlighted diff viewers.

## System Architecture

The core of CodeSentinel AI revolves around a continuous feedback loop among four specialized agents:

1. Analyzer Agent: 
   - Ingests the target repository or script.
   - Executes non-blocking system tool calls (Pylint, Bandit, AST analysis) in thread pools.
   - Aggregates raw, deterministic metrics regarding syntax validity and security context.

2. Planner Agent: 
   - Processes the Analyzer's report.
   - Formulates a step-by-step execution plan to remediate detected issues while preserving the original business logic.

3. Fixer Agent: 
   - Executes the remediation plan.
   - Performs localized code modifications, adhering to PEP-8 standards and fixing recognized security flaws (e.g., hardcoded secrets, injection vulnerabilities).

4. Verifier Agent: 
   - Re-evaluates the modified code against the original constraints.
   - Triggers a rollback or secondary fix cycle if the new code introduces syntax errors.

## Directory Structure
```text
LUMIQ_AI_CodeSentinalAI/
├── backend/
│   ├── agents/          # Core logic for ReAct agents
│   ├── tools/           # Wrappers for Bandit, Pylint, Pytest, AST
│   ├── config.py        # Environment and LLM configuration
│   ├── main.py          # FastAPI application and WebSocket routing
│   └── orchestrator.py  # Manages the pipeline state and data handoffs
├── frontend/
│   ├── css/             # Light theme styling
│   ├── js/              # WebSocket client and UI state management
│   └── index.html       # Dashboard interface
├── requirements.txt     # Python dependencies
├── README.md            # Project documentation
└── ARCHITECTURE.md      # Detailed system flow diagram
```

## Technical Stack
- Backend System: Python 3.9+, FastAPI, Uvicorn, Asyncio, WebSockets
- Agentic Engine: Local LLM (Ollama hosting LLaMA 3) via native HTTP integrations
- Static Analysis: AST, Pylint, Bandit, Radon, Pytest
- Frontend Interface: Vanilla HTML5, CSS3 Custom Properties, Vanilla JavaScript

## Setup and Installation

### Prerequisites
- Python 3.9 or higher
- Ollama installed locally with the llama3 model pulled (`ollama run llama3`)
- Git

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/Nithinchalamchala/LUMIQ_AI_CodeSentinalAI.git
   cd LUMIQ_AI_CodeSentinalAI
   ```

2. Create and activate a virtual environment:
   ```bash
   # Unix/macOS
   python3 -m venv venv
   source venv/bin/activate
   
   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Launch the application:
   ```bash
   uvicorn backend.main:app --reload
   ```

5. Access the user interface:
   Open a web browser and navigate to: http://127.0.0.1:8000

## Usage Guide
1. Ensure your local Ollama instance is running in the background.
2. Open the CodeSentinel AI dashboard on localhost.
3. Input the absolute path of a local project directory or a public Git repository URL.
4. Click "Launch Code Review".
5. Observe the real-time WebSocket feed displaying the granular progression of the Analyzer, Planner, Fixer, and Verifier.
6. Evaluate the presented code diffs to approve the synthesized security and quality improvements.

## Future Scope
- CI/CD Pipeline Integration (GitHub Actions / GitLab CI)
- Expansion of compatibility layers for JavaScript/TypeScript, Go, and Rust.
- Containerization using Docker for isolated execution of the generated code.
