# CodeSentinel AI

## Overview
CodeSentinel AI is an autonomous, multi-agent code review pipeline designed to analyze, plan, fix, and verify code quality. Built upon the ReAct (Reasoning and Acting) agentic architecture, it orchestrates multiple specialized AI agents working alongside deterministic static analysis tools to identify and remediate vulnerabilities, logic errors, and anti-patterns.

## Architecture

The system utilizes a decentralized agent workflow powered by a local Large Language Model (LLaMA 3 via Ollama) and a real-time event streaming backend:

1. Analyzer Agent: Parses abstract syntax trees (AST) and coordinates deterministic tools (Pylint, Bandit, Radon) to gather factual intelligence about the codebase without LLM hallucination.
2. Planner Agent: Synthesizes the analysis reports to formulate a step-by-step remediation strategy.
3. Fixer Agent: Executes the planned changes, rewriting the code to apply fixes.
4. Verifier Agent: Validates the applied fixes against security and syntax standards to ensure structural integrity post-modification.

The backend is built with FastAPI and utilizes WebSockets to stream the agents' internal thought processes directly to a clean, glassmorphism-styled frontend UI.

## Technical Stack
- Backend: Python, FastAPI, Uvicorn, WebSockets, asyncio
- AI Integration: Local LLM (Ollama / LLaMA 3) via native HTTP integrations
- Analysis Tools: AST, Pylint, Bandit, Radon, Pytest
- Frontend: Vanilla HTML, CSS (Light Theme), JavaScript

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

2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the backend server:
   ```bash
   uvicorn backend.main:app --reload
   ```

5. Access the application:
   Open a web browser and navigate to http://127.0.0.1:8000

## Usage
1. Configure a Local Path or Git repository URL in the UI.
2. Click "Launch Code Review".
3. Monitor the live WebSocket feed as the agents observe, think, act, and verify the codebase.
4. Review the generated Diff viewer for the concrete code changes before applying or merging.
