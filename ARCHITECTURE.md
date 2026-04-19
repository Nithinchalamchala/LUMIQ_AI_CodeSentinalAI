# 🏛️ Architecture & System Design

This document provides a high-level overview of the CodeSentinel AI architecture. Use this as a guide to explain the system's data flow, concurrency models, and agentic loop.

## 📊 1. System Architecture Diagram

```mermaid
flowchart TB
    %% Define Styles
    classDef frontend fill:#1e1e2f,stroke:#4a4a6a,stroke-width:2px,color:#fff,rx:5px,ry:5px
    classDef backend fill:#25254b,stroke:#5c5c8a,stroke-width:2px,color:#fff,rx:5px,ry:5px
    classDef agent fill:#3d2b56,stroke:#7b5aab,stroke-width:2px,color:#fff,rx:5px,ry:5px
    classDef tool fill:#1b4332,stroke:#48bb78,stroke-width:2px,color:#fff,rx:5px,ry:5px
    classDef external fill:#4a154b,stroke:#d53f8c,stroke-width:2px,color:#fff,rx:5px,ry:5px

    subgraph Client ["🖥️ Web Client (Frontend)"]
        direction TB
        UI["Glassmorphism Dashboard<br/>(HTML, CSS, Vanilla JS)"]:::frontend
    end

    subgraph Server ["⚡ Server Layer (FastAPI)"]
        direction TB
        REST["REST API Endpoints"]:::backend
        WS["WebSocket Manager<br/>(Live Event Stream)"]:::backend
        Orchestrator["🧠 Pipeline Orchestrator<br/>(State & Retry Logic)"]:::backend
    end

    subgraph Agents ["🤖 Autonomous Multi-Agent Pipeline"]
        direction LR
        A1["🔍 Analyzer<br/>(Scans codebase)"]:::agent
        A2["📋 Planner<br/>(Creates FixPlan)"]:::agent
        A3["🔧 Fixer<br/>(Applies code changes)"]:::agent
        A4["✅ Verifier<br/>(Runs tests)"]:::agent
        
        A1 -->|Raw Issues| A2
        A2 -->|Fix Plan| A3
        A3 -->|Modified Files| A4
        A4 -.->|"Test Traceback<br/>(Self-Healing Loop)"| A3
    end

    subgraph Tools ["🛠️ Deterministic Static Analysis Tools"]
        direction TB
        AST["Python AST<br/>(Syntax & Structure)"]:::tool
        Pylint["Pylint<br/>(Style & Practices)"]:::tool
        Bandit["Bandit<br/>(Security Vulnerabilities)"]:::tool
        Pytest["Pytest<br/>(Regression Tests)"]:::tool
    end

    subgraph Infrastructure ["🌍 External Infrastructure"]
        direction TB
        LLM["Local LLM API<br/>(Ollama / LLaMA 3)"]:::external
        FileSystem["/tmp Sandbox<br/>(Cloned Git Repository)"]:::external
    end

    %% Wiring it all together
    UI <-->|HTTP POST / GET| REST
    UI <-->|ws:// Events| WS
    REST -->|Triggers Pipeline| Orchestrator
    Orchestrator -.->|Dispatches Live Logs| WS
    
    Orchestrator -->|1. Git Clone| FileSystem
    Orchestrator -->|2. Start Pipeline| A1
    
    A1 -->|Executes tools| AST & Pylint & Bandit
    A4 -->|Executes tests| Pytest
    
    AST & Pylint & Bandit --> FileSystem
    Pytest --> FileSystem
    A3 -->|Writes Patches| FileSystem
    
    A1 & A2 & A3 & A4 <-->|POST Prompt Requests| LLM
```

## 🔄 2. Data Flow & Execution Walkthrough

When you explain the architecture in a video or interview, follow this 5-step flow:

### Step 1: The Request (Frontend ➔ FastAPI)
The user submits a GitHub URL or a Local Path via the UI. **FastAPI** establishes a **WebSocket** connection immediately so the frontend can listen to live updates.

### Step 2: The Sandbox (Orchestrator)
The **Orchestrator** intercepts the request and uses `GitTools` to clone the target repository into an isolated `/tmp` workspace. This ensures the user's original codebase is never permanently corrupted by AI changes.

### Step 3: Analysis (Anti-Hallucination)
The Orchestrator wakes up the **Analyzer Agent**. 
* **The Magic:** To prevent the LLM from hallucinating bugs, the Analyzer offloads the file reading to *deterministic Python tools* (`ast`, `pylint`, `bandit`). 
* Because these tools are CPU-bound and slow on large repos, they are pushed to a background thread using `asyncio.to_thread()`, keeping the FastAPI WebSocket alive and responsive.
* Once the tools return hard data (exact line numbers and severities), the Analyzer pings the **Local LLM (Ollama)** to write human-readable descriptions of the issues.

### Step 4: The ReAct Handoffs (Planner ➔ Fixer)
* **Planner Agent:** Takes the JSON list of issues, sends it to the LLM, and generates a strict, prioritized `FixPlan` (focusing on Critical/High bugs first).
* **Fixer Agent:** Reads the `FixPlan`, reads the specific files needing repairs, and uses the LLM to generate patched code, replacing the bad code on the disk in the temporary sandbox.

### Step 5: The Self-Healing Loop (Verifier)
* **Verifier Agent:** Runs `pytest` and `ast` syntax checks against the patched code. 
* **The Retry Loop:** If the test fails or throws a Python syntax error, the Orchestrator catches the traceback, sends it back to the Fixer Agent, and triggers a retry loop (`attempt < MAX_RETRIES`). The AI essentially debugs its own code before the user ever sees it.
* Once verified, the final payload—issues, fix plans, code diffs, and execution traces—is served back to the Frontend.

## 🧠 3. Core Principles
* **Separation of Concerns:** Using specialized agents makes prompting the LLM much cheaper and more accurate than asking one giant AI to do everything at once.
* **Deterministic Boundaries:** Using real tools (`pylint`, `ast`) restricts the AI from guessing.
* **Non-blocking IO:** FastAPI event loops handle networking while `asyncio.to_thread` handles the heavy code parsing.
